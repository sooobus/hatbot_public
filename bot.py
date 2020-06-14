#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import random
import threading
import time
from datetime import datetime

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

import prod_config
import staging_config
import texts
from db import start_game, HatWrapper, Game, Hat
from round import Round

logger = logging.getLogger(__name__)
hat: Hat
game: Game

allowed_rooms = list(map(str.strip, open("rooms.txt", encoding='utf8').readlines()))
experimental_rooms = list(map(str.strip, open("experimental_rooms.txt", encoding='utf8').readlines()))
personal_rooms = list(map(str.strip, open("personal_rooms.txt", encoding='utf8').readlines()))
dictionaries = {}


def read_dictionaries():
    result = {}
    dictionary_names = list(map(str.strip, open("dictionaries/list.txt", encoding='utf8').readlines()))
    for dictionary_name in dictionary_names:
        result[dictionary_name] = list(
            map(str.strip, open("dictionaries/" + dictionary_name + ".txt", encoding='utf8').readlines()))
    return result


def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text(texts.start_message)


def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text(texts.help_message)


buttons = ["угадано!", "ошибка :(", "всё."]
ready_button = ["хочу слово!"]

reply_markup_game = ReplyKeyboardMarkup.from_column(buttons)
reply_markup_ready = ReplyKeyboardMarkup.from_column(ready_button)


def pretty_turn(turn, context):
    return "{} -> {}".format(context.bot_data["username" + str(turn[0])], context.bot_data["username" + str(turn[1])])


def handle_timer(context, room, timer, message):
    iteration = 0
    while iteration < timer and not "abort_timer_message" + room in context.bot_data:
        time.sleep(1)
        iteration += 1
        message.edit_text(str(iteration))
    if "abort_timer_message" + room in context.bot_data:
        message.edit_text(texts.timer_aborted_message.format(context.bot_data["abort_timer_message" + room]))
    else:
        message.edit_text(texts.timer_stopped_message)
        for user in context.bot_data["room" + room]:
            context.bot.send_message(context.bot_data["chatid" + str(user)], texts.timer_finished_message)


def start_turn(update, context):
    user = update.message.from_user
    text = update.message.text.lower()
    user_id = user['id']
    room = game.room_for_player(user_id)
    if context.bot_data["round" + room].timer:
        context.bot_data.pop("abort_timer_message" + room, None)
        timer_message = update.message.reply_text(str(0))
        thread = threading.Thread(target=handle_timer, args=(context, room,
                                                             context.bot_data["round" + room].timer, timer_message))
        thread.start()
    logger.info("start_turn %d %s", user_id, text)
    for user in context.bot_data["room" + room]:
        context.bot.send_message(context.bot_data["chatid" + str(user)], texts.turn_started_message)
    reply = context.bot_data["round" + room].start_move(user_id)
    update.message.reply_text(reply, reply_markup=reply_markup_game)


def send_results_to_all(context, room):
    scores = context.bot_data["round" + room].pretty_scores()
    scores_names = ["{}: {}".format(context.bot_data["username" + str(k)], v) for k, v in scores]
    reply = "\n".join(scores_names)
    for user in context.bot_data["room" + room]:
        context.bot.send_message(context.bot_data["chatid" + str(user)],
                                 reply,
                                 reply_markup=ReplyKeyboardRemove())


def results(update, context):
    user = update.message.from_user
    user_id = user['id']
    room = game.room_for_player(user_id)
    logger.info("results %d", user_id)
    scores = context.bot_data["round" + room].pretty_scores()
    scores_names = []
    for player, total_score, explained_score, guessed_score in scores:
        player_username = context.bot_data["username" + str(player)]
        scores_names.append("{}: {}+{}={}".format(player_username, explained_score, guessed_score, total_score))
    reply = "\n".join(scores_names)
    update.message.reply_text(reply)


def finish_round(update, context):
    user = update.message.from_user
    user_id = user['id']
    room = game.room_for_player(user_id)
    send_results_to_all(context, room)
    users_to_kick = list(context.bot_data["room" + room])
    print(users_to_kick)
    for user in users_to_kick:
        leaveroom_player(user, context.bot_data["chatid" + str(user)], context)


def continue_turn(update, context):
    user_data = update.message.from_user
    text = update.message.text.lower()
    user_id = user_data['id']
    room = game.room_for_player(user_id)
    logger.info("continue_turn %d %s", user_id, text)
    if text == "угадано!":
        reply = context.bot_data["round" + room].guessed(user_id)
        update.message.reply_text(reply, reply_markup=reply_markup_game)
        return
    elif text == "ошибка :(":
        context.bot_data["abort_timer_message" + room] = text
        turn = context.bot_data["round" + room].failed(user_id)
        reply = pretty_turn(turn, context)
    elif text == "всё.":
        context.bot_data["abort_timer_message" + room] = text
        turn = context.bot_data["round" + room].time_ran_out(user_id)
        reply = pretty_turn(turn, context)

    for user in context.bot_data["room" + room]:
        if user == turn[0]:
            context.bot.send_message(context.bot_data["chatid" + str(user)], reply, reply_markup=reply_markup_ready)
        else:
            context.bot.send_message(context.bot_data["chatid" + str(user)], reply, reply_markup=ReplyKeyboardRemove())


def echo(update, context):
    """Echo the user message."""
    user = update.message.from_user
    text = update.message.text.lower()
    user_id = user['id']
    room = game.room_for_player(user_id)
    logger.info("ECHO %d %s", user_id, text)
    reply_markup = None
    if "settimer" in context.user_data and context.user_data["settimer"]:
        timer = int(text) if text.isdigit() and 0 < len(text) < 4 else -1
        if 0 <= timer <= 300:
            reply = texts.timer_set_message.format(timer)
            if timer == 0:
                timer = None
                reply = texts.timer_unset_message
            if "round" + room in context.bot_data:
                context.bot_data["round" + room].timer = timer
            context.bot_data["timer" + room] = timer
        else:
            reply = texts.invalid_timer_format_message
        context.user_data["settimer"] = False
        update.message.reply_text(reply)
        return
    if "removeword" in context.user_data and context.user_data["removeword"]:
        status = hat.remove_word(text, room)
        if status:
            reply = texts.removed_word_message
        else:
            reply = texts.not_removed_word_message
        context.user_data["removeword"] = False
        update.message.reply_text(reply)
        return
    reply = None
    if room:
        words = text.split()
        if len(words) == 2 and words[0] in dictionaries and words[1].isdigit():
            # Add words from dictionary
            reply = add_words_from_dictionary(room, user_id, words)
        elif room:
            # Add word(s)
            reply = add_single_or_multiple_words(room, user_id, words)
    if reply is None:
        # Add user to the room
        print(text)
        text = text.lower()
        if text in allowed_rooms or text in personal_rooms:
            game.add_player(user_id, text)
            reply = texts.room_greeting_message.format(text, hat.words_in_hat(text))
        elif text in experimental_rooms:
            game.add_player(user_id, text)
            reply = texts.welcome_exp
        else:
            reply = texts.no_such_rooms_message
    update.message.reply_text(reply, reply_markup=reply_markup)


def add_single_or_multiple_words(room, user_id, words):
    if len(words) == 1:
        status = hat.add_word(words[0], user_id, room)
        if status:
            reply = texts.word_added_message.format(hat.words_in_hat(room))
        else:
            reply = texts.word_not_added_message
    else:
        added_word_count = 0
        skipped_words = []
        for word in words:
            if hat.add_word(word, user_id, room):
                added_word_count += 1
            else:
                skipped_words.append(word)
        skipped_words_string = ", ".join(skipped_words)
        if len(skipped_words) > 0 and len(skipped_words_string) < 200:
            reply = texts.words_added_skipped_words_message.format(added_word_count, skipped_words_string,
                                                                   hat.words_in_hat(room))
        else:
            reply = texts.words_added_skip_count_message.format(added_word_count, len(skipped_words),
                                                                hat.words_in_hat(room))
    return reply


def add_words_from_dictionary(room, user_id, words):
    dictionary_name = words[0]
    to_add_word_count = int(words[1])
    if to_add_word_count <= 0 or to_add_word_count > hat.max_word_count():
        return texts.illegal_to_add_word_count_message.format(hat.max_word_count())
    if hat.words_in_hat(room) + to_add_word_count > hat.max_word_count():
        return texts.illegal_total_word_count_message.format(hat.max_word_count())
    added_word_count = 0
    while added_word_count < to_add_word_count:
        add_words = random.sample(dictionaries[dictionary_name], to_add_word_count - added_word_count)
        for word in add_words:
            if hat.add_word(word, user_id, room):
                added_word_count += 1
    reply = texts.words_added_from_dictionary_message.format(dictionary_name, added_word_count, hat.words_in_hat(room))
    return reply


def removeword(update, context):
    user = update.message.from_user
    user_id = user['id']
    room = game.room_for_player(user_id)
    if room:
        context.user_data["removeword"] = True
        update.message.reply_text(texts.please_remove_word_message)
    else:
        update.message.reply_text(texts.no_remove_from_hall_message)


def settimer(update, context):
    user = update.message.from_user
    user_id = user['id']
    room = game.room_for_player(user_id)
    if room:
        context.user_data["settimer"] = True
        update.message.reply_text(texts.please_settimer_message)
    else:
        update.message.reply_text(texts.no_settimer_from_hall_message)


def getword(update, context):
    user = update.message.from_user
    user_id = user['id']
    room = game.room_for_player(user_id)
    logger.info("GETWORD %d", user_id)
    if room:
        word = hat.get_word(room)
        if word:
            reply = word
        else:
            reply = texts.words_finished_message
    else:
        reply = texts.getword_from_hall_message
    update.message.reply_text(reply)


def check_ready(room, context):
    if game.room_size(room) > 1 and (len(context.bot_data["room" + room]) == game.room_size(room)):
        return True
    else:
        return False


def start_round(room, context):
    reply = texts.everyone_ready
    hatwr = HatWrapper(room, hat)
    if len(context.bot_data["room" + room]) < 2:
        reply = "Для начала игры нужно хотя бы два игрока"
        turn = (0, 0)
    else:
        context.bot_data["round" + room] = Round(hatwr, list(context.bot_data["room" + room]))
        if "timer" + room in context.bot_data:
            context.bot_data["round" + room].timer = context.bot_data["timer" + room]
        turn = context.bot_data["round" + room].start_game()
        reply += pretty_turn(turn, context)
    for user in context.bot_data["room" + room]:
        reply_markup = None
        if user == turn[0]:
            reply_markup = reply_markup_ready
        context.bot.send_message(context.bot_data["chatid" + str(user)], reply,
                                 reply_markup=reply_markup)


def force_start(update, context):
    user = update.message.from_user
    user_id = user['id']
    room = game.room_for_player(user_id)
    start_round(room, context)


def ready(update, context):
    user = update.message.from_user
    user_id = user['id']
    room = game.room_for_player(user_id)
    logger.info("READY %d", user_id)
    reply_markup = None
    if room:
        context.bot_data["chatid" + str(user_id)] = update.message.chat.id
        context.bot_data["username" + str(user_id)] = user['first_name']
        if "room" + room in context.bot_data:
            context.bot_data["room" + room].add(user_id)
        else:
            context.bot_data["room" + room] = {user_id}
        reply = texts.ready
        if check_ready(room, context):
            start_round(room, context)
            return
    else:
        reply = ":("
    update.message.reply_text(reply, reply_markup=reply_markup)


def leaveroom_player(user_id, chat_id, context):
    room = game.room_for_player(user_id)
    print(room)
    if "room" + room in context.bot_data:
        if user_id in context.bot_data["room" + room]:
            context.bot_data["room" + room].remove(user_id)
    game.leave_room(user_id)
    context.bot.send_message(chat_id, texts.room_left)


def leaveroom(update, context):
    user = update.message.from_user
    user_id = user['id']
    leaveroom_player(user_id, update.message.chat.id, context)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    configs = {'prod': prod_config,
               'staging': staging_config,
               }

    parser = argparse.ArgumentParser(description='Hat bot')
    parser.add_argument('db_file', help='SQLite database file')
    parser.add_argument('log_file', help='Log file name')
    parser.add_argument('config', help='Environment', choices=list(configs.keys()))
    args = parser.parse_args()

    config = configs[args.config]

    # Initialize random from time for later use
    random.seed(datetime.now())

    # Read dictionary files into RAM
    global dictionaries
    dictionaries = read_dictionaries()

    logging.basicConfig(filename=args.log_file,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

    global hat, game
    hat, game = start_game(args.db_file)

    updater = Updater(token=config.token, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("getword", getword))
    dp.add_handler(CommandHandler("leaveroom", leaveroom))
    dp.add_handler(CommandHandler("removeword", removeword))
    dp.add_handler(CommandHandler("settimer", settimer))
    dp.add_handler(CommandHandler("ready", ready))
    dp.add_handler(CommandHandler("results", results))
    dp.add_handler(CommandHandler("force_start", force_start))
    dp.add_handler(CommandHandler("finish_round", finish_round))
    dp.add_handler(MessageHandler(Filters.text(ready_button), start_turn))
    dp.add_handler(MessageHandler(Filters.text(buttons), continue_turn))
    dp.add_handler(MessageHandler(Filters.text, echo))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
