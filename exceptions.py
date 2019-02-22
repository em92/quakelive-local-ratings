# -*- coding: utf-8 -*-


class InvalidMatchReport(Exception):
    pass


class MatchAlreadyExists(InvalidMatchReport):
    pass


class InvalidGametype(Exception):
    pass
