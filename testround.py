import unittest
from round import Round, Move


class WordCollection:
    def __init__(self):
        self.put_back_cnt = 0

    def get_word(self):
        return ("one")

    def add_word(self, word, player):
        self.put_back_cnt += 1
        return True


class TestMove(unittest.TestCase):
    def test_moves(self):
        move = Move([1, 2, 3])
        self.assertEqual(next(move), (1, 2))
        self.assertEqual(next(move), (2, 3))
        self.assertEqual(next(move), (3, 1))
        self.assertEqual(next(move), (1, 3))
        self.assertEqual(next(move), (2, 1))
        self.assertEqual(next(move), (3, 2))
        self.assertEqual(next(move), (1, 2))
        self.assertEqual(next(move), (2, 3))
        self.assertEqual(next(move), (3, 1))


class TestRound(unittest.TestCase):
    def test_standard_moves(self):
        r = Round(WordCollection(), [0, 1, 2])
        self.assertEqual(r.start_game(), (0, 1))
        self.assertEqual(r.start_move(0), "one")
        self.assertEqual(r.guessed(0), "one")
        self.assertEqual(r.time_ran_out(0), (1, 2))
        self.assertEqual(r.start_move(1), "one")
        self.assertEqual(r.failed(1), (2, 0))
        self.assertEqual(r.start_move(2), "one")
        self.assertEqual(r.guessed(2), "one")
        self.assertEqual(r.guessed(2), "one")
        self.assertEqual(r.guessed(2), "one")
        self.assertEqual(r.guessed(2), "one")
        self.assertEqual(r.pretty_scores(), [(0, 5), (2, 4), (1, 1)])


if __name__ == '__main__':
    unittest.main()
