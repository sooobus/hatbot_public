import unittest

import texts
from round import Round, Move


class SingleWordCollection:
    def __init__(self):
        self.put_back_cnt = 0

    def get_word(self):
        return "one"

    def add_word(self, word, player):
        self.put_back_cnt += 1
        return True


class ManyWordCollection:
    def __init__(self):
        self.words = {"два", "двенадцать", "восемьдесят", "пять", "ноль", "шесть"}

    def get_word(self):
        if not self.words:
            return None
        return self.words.pop()

    def add_word(self, word, player):
        if word in self.words:
            raise NotImplementedError
        self.words.add(word)


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
        r = Round(SingleWordCollection(), [0, 1, 2])
        self.assertFalse(r.timer)
        r.timer = 25
        self.assertEqual(r.timer, 25)
        r.timer = 30
        self.assertEqual(r.timer, 30)
        r.timer = None
        self.assertFalse(r.timer)
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
        self.assertEqual(r.pretty_scores(), [[0, 5, 1, 4], [2, 4, 4, 0], [1, 1, 0, 1]])

    def test_more_words(self):
        r = Round(ManyWordCollection(), [0, 1, 2])

        self.assertEqual(r.start_game(), (0, 1))
        got = set()
        got.add(r.start_move(0))
        got.add(r.guessed(0))
        got.add(r.guessed(0))
        self.assertEqual(r.time_ran_out(0), (1, 2))
        self.assertEqual(r.guessed(0), texts.not_your_turn_message)

        got.add(r.start_move(1))
        got.add(r.guessed(1))
        self.assertEqual(r.time_ran_out(1), (2, 0))

        got.add(r.start_move(2))
        self.assertEqual(r.time_ran_out(2), (0, 2))

        got.add(r.start_move(0))
        got.add(r.guessed(0))
        self.assertEqual(r.time_ran_out(0), (1, 0))

        got.add(r.start_move(1))
        got.add(r.guessed(1))
        self.assertEqual(r.time_ran_out(1), (2, 1))

        got.add(r.start_move(2))
        self.assertEqual(r.failed(2), (0, 1))
        self.assertEqual(r.guessed(2), texts.not_your_turn_message)

        self.assertEqual(r.start_move(0), texts.no_more_words_message)
        self.assertSetEqual(got, {"два", "двенадцать", "восемьдесят", "пять", "ноль", "шесть"})

        self.assertEqual(r.points[0], 4)
        self.assertEqual(r.points[1], 4)
        self.assertEqual(r.points[2], 2)


if __name__ == '__main__':
    unittest.main()
