class InvalidMatchReport(Exception):
    pass


class MatchAlreadyExists(InvalidMatchReport):
    pass


class InvalidGametype(Exception):
    pass


class MatchNotFound(Exception):
    pass


class PlayerNotFound(Exception):
    pass
