import os
import tempfile
import unittest

from db import start_game


class TestDb(unittest.TestCase):
    def setUp(self):
        self.fd, self.db_file = tempfile.mkstemp()

    def tearDown(self):
        os.close(self.fd)
        os.remove(self.db_file)

    def test_db(self):
        hat, game = start_game(self.db_file)
        self.assertIsNone(game.room_for_player(1))
        game.add_player(1, "room1")
        game.add_player(3, "room2")
        game.add_player(2, "room1")
        game.add_player(4, "room2")
        self.assertEqual(game.room_size("room1"), 2)
        self.assertEqual(game.room_size("room2"), 2)
        self.assertEqual(game.room_for_player(2), "room1")
        self.assertIsNone(hat.get_word("room1"))
        self.assertTrue(hat.add_word("первое", 1, "room1"))
        self.assertTrue(hat.add_word("second", 1, "room1"))
        self.assertEqual(hat.words_in_hat("room1"), 2)
        self.assertTrue(hat.add_word("треТье", 1, "room1"))
        self.assertFalse(hat.remove_word("кусь", "room1"))
        self.assertTrue(hat.add_word("чеТвертое", 1, "room1"))
        self.assertTrue(hat.add_word("пятое", 1, "room1"))
        self.assertTrue(hat.remove_word("пятое", "room1"))
        self.assertFalse(hat.add_word("qcь", 1, "room1"))
        self.assertFalse(hat.add_word("", 1, "room1"))
        self.assertFalse(hat.add_word("первое", 1, "room1"))
        self.assertTrue(hat.get_word("room1"))
        self.assertTrue(hat.get_word("room1"))
        self.assertTrue(hat.get_word("room1"))
        self.assertTrue(hat.get_word("room1"))
        self.assertIsNone(hat.get_word("room1"))


if __name__ == '__main__':
    unittest.main()
