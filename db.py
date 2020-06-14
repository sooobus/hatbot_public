import random
import sqlite3
import threading
from sqlite3 import Error
from typing import Iterable

create_table_players_q = """ CREATE TABLE IF NOT EXISTS players (
                                id integer PRIMARY KEY,
                                room text ); """
create_table_words_q = """ CREATE TABLE IF NOT EXISTS words (
                                word text,
                                author integer,
                                room text,
                                used integer ); """
add_word_q = """ INSERT INTO words(word, author, room, used) VALUES(?, ?, ?, 0);"""
get_word_q = """ SELECT word FROM words WHERE room=? AND used=0; """
mark_word_used_q = """ UPDATE words
                       SET used=1
                       WHERE (word=? AND room=?);"""

find_unused_word_q = """ SELECT word FROM words WHERE word=? AND used=0 AND room=?; """
num_words_in_hat_q = """ SELECT COUNT(word) as num FROM words WHERE used=0 AND room=?; """
add_player_q = """ INSERT INTO players(id, room) VALUES(?, ?);"""
find_player_room_q = """ SELECT room FROM players WHERE id=?;"""
remove_player_room_q = """ DELETE FROM players
                       WHERE (id=?);"""
room_count_q = """ SELECT COUNT(id) FROM players WHERE room=?;"""


def try_execute(cursor: sqlite3.Cursor, sql: str, parameters: Iterable = ...):
    try:
        cursor.execute(sql, parameters)
        return True
    except Error as e:
        print(e)
        return False


def check_word(word: str):
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


def get_local_cursor(data, db_file):
    def cursor():
        if 'conn' not in data.__dict__:
            # isolation_level = None enables autocommit mode
            # see https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.isolation_level
            data.conn = sqlite3.connect(db_file, isolation_level=None)
            data.cursor = data.conn.cursor()
        return data.cursor

    return cursor


class Hat:
    def __init__(self, db_file):
        self.data = threading.local()
        self.cursor = get_local_cursor(self.data, db_file)
        self.cursor().execute(create_table_words_q)

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
        if self.cursor().execute(find_unused_word_q, (word, room)).fetchall():
            return False
        return try_execute(self.cursor(), add_word_q, (word, player_id, room))

    def get_word(self, room):
        words = self.cursor().execute(get_word_q, (room,)).fetchall()
        if not words:
            return None
        word = random.choice(words)[0]
        if try_execute(self.cursor(), mark_word_used_q, (word, room)):
            return word
        else:
            return None

    def remove_word(self, word, room):
        if not self.cursor().execute(find_unused_word_q, (word, room)).fetchall():
            return False
        return try_execute(self.cursor(), mark_word_used_q, (word, room))

    def words_in_hat(self, room):
        words_num = self.cursor().execute(num_words_in_hat_q, (room,)).fetchall()
        if not words_num:
            return None
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
        self.data = threading.local()
        self.cursor = get_local_cursor(self.data, db_file)
        self.cursor().execute(create_table_players_q)

    def add_player(self, player_id, room):
        self.cursor().execute(add_player_q, (player_id, room))

    def leave_room(self, player_id):
        self.cursor().execute(remove_player_room_q, (player_id,))

    def room_for_player(self, player_id):
        result = self.cursor().execute(find_player_room_q, (player_id,)).fetchall()
        if result:
            return result[0][0]
        else:
            return None

    def room_size(self, room):
        result = self.cursor().execute(room_count_q, (room,)).fetchall()
        if result:
            return result[0][0]
        else:
            return None


def start_game(db_file):
    hat = Hat(db_file)
    game = Game(db_file)
    return hat, game


def tests():
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
    assert hat.words_in_hat("room1") == 2
    assert hat.add_word("треТье", 1, "room1")
    assert not hat.remove_word("кусь", "room1")
    assert hat.add_word("чеТвертое", 1, "room1")
    assert hat.add_word("пятое", 1, "room1")
    assert hat.remove_word("пятое", "room1")
    assert not hat.add_word("qcь", 1, "room1")
    assert hat.get_word("room1")
    assert hat.get_word("room1")
    assert hat.get_word("room1")
    assert hat.get_word("room1")
    assert hat.get_word("room1") is None


if __name__ == '__main__':
    tests()
