import sqlite3
import random

from sqlite3 import Error

create_table_players_q = """ CREATE TABLE IF NOT EXISTS players (
                                id integer PRIMARY KEY,
                                room text ); """
create_table_words_q = """ CREATE TABLE IF NOT EXISTS words (
                                word text,
                                author integer,
                                room text,
                                used integer ); """
add_word_q = """ INSERT INTO words(word, author, room, used) VALUES("{}", {}, "{}", 0);"""
get_word_q = """ SELECT word FROM words WHERE room="{}" AND used=0; """
mark_word_used_q = """ UPDATE words
                       SET used=1
                       WHERE (word="{}" AND room="{}");"""

find_unused_word_q = """ SELECT word FROM words WHERE word="{}" AND used=0 AND room="{}"; """
num_words_in_hat_q = """ SELECT COUNT(word) as num FROM words WHERE used=0 AND room="{}"; """
add_player_q = """ INSERT INTO players(id, room) VALUES({}, "{}");"""
find_player_room_q = """ SELECT room FROM players WHERE id={};"""
remove_player_room_q = """ DELETE FROM players
                       WHERE (id={});"""
room_count_q = """ SELECT COUNT(id) FROM players WHERE room="{}";"""


def create_connection(db_file):
    """ create a database connection to a SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        print(e)
    return conn


def execute_sql(db_file, sql):
    conn = create_connection(db_file)
    try:
        c = conn.cursor()
        c.execute(sql)
        conn.commit()
        conn.close()
        return True
    except Error as e:
        print(e)
        return False


def execute_sql_select(db_file, sql):
    conn = create_connection(db_file)
    try:
        c = conn.cursor()
        c.execute(sql)
        ans = c.fetchall()
        c.close()
        return ans
    except Error as e:
        print(e)


def check_word(word):
    def check_rus(word):
        for c in word:
            if not (('а' <= c <= 'я') or c == '-' or c == 'ё'):
                return False
        return True

    def check_en(word):
        for c in word:
            if not (('a' <= c <= 'z') or c == '-'):
                return False
        return True

    if not len(word):
        return False

    return check_rus(word) or check_en(word)


class Hat:
    def __init__(self, db_file):
        self.db_file = db_file
        execute_sql(self.db_file, create_table_words_q)

    @staticmethod
    def max_word_count():
        return 1000

    @staticmethod
    def max_word_length():
        return 200

    def add_word(self, word, player_id, room):
        word = word.lower()
        if not check_word(word)\
                or len(word) > self.max_word_length() or self.words_in_hat(room) >= self.max_word_count():
            return False
        else:
            query = find_unused_word_q.format(word, room)
            res = execute_sql_select(self.db_file, query)
            if res:
                return False
            query = add_word_q.format(word, player_id, room)
            return execute_sql(self.db_file, query)

    def get_word(self, room):
        words = execute_sql_select(self.db_file, get_word_q.format(room))
        if not words:
            return None
        word = random.choice(words)[0]
        if execute_sql(self.db_file, mark_word_used_q.format(word, room)):
            return word
        else:
            return "Не удалось вернуть слово в шляпу"

    def remove_word(self, word, room):
        query = find_unused_word_q.format(word, room)
        res = execute_sql_select(self.db_file, query)
        if not res:
            return False
        status = execute_sql(self.db_file, mark_word_used_q.format(word, room))
        return status

    def words_in_hat(self, room):
        words_num = execute_sql_select(self.db_file, num_words_in_hat_q.format(room))
        if not words_num:
            return ""
        return words_num[0][0]


class HatWrapper:
    def __init__(self, room, hat):
        self.room = room
        self.hat = hat

    def get_word(self):
        word = self.hat.get_word(self.room)
        if not word:
            return None
        return word

    def add_word(self, word, player):
        return self.hat.add_word(word, player, self.room)


class Game:
    def __init__(self, db_file):
        self.db_file = db_file
        execute_sql(self.db_file, create_table_players_q)

    def add_player(self, player_id, room):
        execute_sql(self.db_file, add_player_q.format(player_id, room))

    def leave_room(self, player_id):
        execute_sql(self.db_file, remove_player_room_q.format(player_id))

    def room_for_player(self, player_id):
        rooms = execute_sql_select(self.db_file, find_player_room_q.format(player_id))
        if rooms:
            return rooms[0][0]
        else:
            return None

    def room_size(self, room):
        rooms = execute_sql_select(self.db_file, room_count_q.format(room))
        if rooms:
            return rooms[0][0]
        else:
            return None


def start_game(db_file):
    hat = Hat(db_file)
    game = Game(db_file)
    return hat, game


if __name__ == '__main__':
    hat, game = start_game("test165.db")
    assert game.room_for_player(1) is None
    game.add_player(1, "room1")
    game.add_player(3, "room2")
    game.add_player(2, "room1")
    game.add_player(4, "room2")
    assert game.room_size("room1") == 2
    assert game.room_size("room2") == 2
    assert game.room_for_player(2) == "room1"
    assert hat.get_word("room1") is None
    assert hat.add_word("первое", 1, "room1")
    assert hat.add_word("второе", 1, "room1")
    hat.words_in_hat("room1")
    assert hat.add_word("треТье", 1, "room1")
    assert not hat.remove_word("кусь", "room1")
    assert hat.add_word("чеТвертое", 1, "room1")
    assert hat.add_word("пятое", 1, "room1")
    assert hat.remove_word("пятое", "room1")
    assert not hat.add_word("djfkjsd", 1, "room1")
    assert hat.get_word("room1")
    assert hat.get_word("room1")
    assert hat.get_word("room1")
    assert hat.get_word("room1")
    assert not hat.get_word("room1")
