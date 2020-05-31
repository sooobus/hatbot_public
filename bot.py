#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import sys
import texts
import prod_config
import staging_config

from db import start_game, HatWrapper
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove

from round import Round

logging.basicConfig(filename=sys.argv[2], format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

hat, game = start_game(sys.argv[1])

allowed_rooms = list(map(str.strip, open("rooms.txt").readlines()))
experimental_rooms = list(map(str.strip, open("experimental_rooms.txt").readlines()))
personal_rooms = list(map(str.strip, open("personal_rooms.txt").readlines()))


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


def start_turn(update, context):
    user = update.message.from_user
    text = update.message.text.lower()
    user_id = user['id']
    room = game.room_for_player(user_id)
    logger.info("start_turn %d %s", user_id, text)
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
    scores_names = ["{}: {}".format(context.bot_data["username" + str(k)], v) for k, v in scores]
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
        turn = context.bot_data["round" + room].failed(user_id)
        reply = pretty_turn(turn, context)
    elif text == "всё.":
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
    if "removeword" in context.user_data and context.user_data["removeword"]:
        status = hat.remove_word(text, room)
        if status:
            reply = texts.removed_word_message
        else:
            reply = texts.not_removed_word_message
        context.user_data["removeword"] = False
        update.message.reply_text(reply)
        return
    if room:
        # Add word(s)
        words = text.split()
        if len(words) == 1:
            status = hat.add_word(text, user_id, room)
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
    else:
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


def removeword(update, context):
    user = update.message.from_user
    user_id = user['id']
    room = game.room_for_player(user_id)
    if room:
        context.user_data["removeword"] = True
        update.message.reply_text(texts.please_remove_word_message)
    else:
        update.message.reply_text(texts.no_remove_from_hall_message)


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
            context.bot_data["room" + room] = set([user_id])
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
    """Start the bot."""
    if sys.argv[3] == "prod":
        token = prod_config.token
    elif sys.argv[3] == "staging":
        token = staging_config.token
    else:
        print("Please specify bot version.")
        return
    updater = Updater(token, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("getword", getword))
    dp.add_handler(CommandHandler("leaveroom", leaveroom))
    dp.add_handler(CommandHandler("removeword", removeword))
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
