import itertools
from collections import Counter
from random import shuffle


class Move:
    """ Implements standard Hat algorithm. """

    def __init__(self, players):
        self.players = players
        self.lead = 0
        self.target = 1

    def __next__(self):
        m = len(self.players)
        ret = (self.players[self.lead], self.players[self.target])
        self.lead = (self.lead + 1) % m
        self.target = (self.target + 1) % m
        if self.lead == 0:
            self.target = (self.target + 1) % m
            if self.target == self.lead:
                self.target = (self.target + 1) % m
        return ret

    def __iter__(self):
        return self


class Round:
    def __init__(self, word_collection, players):
        """ Word collection must implement get_word and add_word. """
        self.word_collection = word_collection
        self.players = players
        self.points = Counter()
        self.move = Move(self.players)
        self._timer = None

    def start_game(self):
        if len(self.players) > 1:
            return self.__next_move()

    def start_move(self, player):
        if player == self.lead:
            return self.__next_word(player)
        else:
            return "Сейчас не ваш ход"

    def guessed(self, player):
        """ Increments player's points. """
        if player == self.lead:
            self.points[player] += 1
            self.points[self.target] += 1
            return self.__next_word(player)
        else:
            return "Сейчас не ваш ход"

    def failed(self, player):
        """ Passes the turn to the next player. """
        if player == self.lead:
            return self.__next_move()
        else:
            return "Сейчас не ваш ход"

    def time_ran_out(self, player):
        """ Puts the word back and passes the turn. """
        if player == self.lead:
            if self.word:
                self.word_collection.add_word(self.word, player)
            return self.__next_move()
        else:
            return "Сейчас не ваш ход"

    def pretty_scores(self):
        return self.points.most_common(len(self.players))

    @property
    def timer(self):
        return self._timer

    @timer.setter
    def timer(self, timer):
        self._timer = timer

    def __next_move(self):
        """ Starts next move and returns players' names. """
        self.lead, self.target = next(self.move)
        return (self.lead, self.target)

    def __next_word(self, player):
        """ Returns the next word to explain. """
        if player == self.lead:
            self.word = self.word_collection.get_word()
            if self.word == None:
                return "Слова закончились"
            return self.word
        else:
            return "Сейчас не ваш ход"
