GAMETYPE_RULES = {}


def detect_by_match_report(data):
    for short, gt in GAMETYPE_RULES.items():
        if gt.force_by_match_report(data):
            return short

    return data["game_meta"]["G"]


class AbstractGametype:
    def calculate_player_perf(self, player_data, time_factor):
        raise NotImplementedError()  # pragma: nocover

    def force_by_match_report(self, data):
        return False

    def override_min_player_count(self):
        return None

    def extra_factor(self, matches, wins, losses):
        return 1

    def medals_in_scoreboard_mid(self):
        return []

    def medals_in_scoreboard_right(self):
        return []


# gametype rules are defined below


class GametypeAD(AbstractGametype):
    def calc_player_perf(self, player_data, time_factor):
        frags_count = int(player_data["scoreboard-kills"])
        capture_count = int(player_data["medal-captures"])
        damage_dealt = int(player_data["scoreboard-pushes"])
        return (damage_dealt / 100 + frags_count + capture_count) * time_factor

    def medals_in_scoreboard_mid(self):
        return ["captures", "defends"]


class GametypeCA(AbstractGametype):
    def calc_player_perf(self, player_data, time_factor):
        frags_count = int(player_data["scoreboard-kills"])
        damage_dealt = int(player_data["scoreboard-pushes"])
        return (damage_dealt / 100 + 0.25 * frags_count) * time_factor


class GametypeCTF(AbstractGametype):
    def calc_player_perf(self, player_data, time_factor):
        score = int(player_data["scoreboard-score"])
        damage_dealt = int(player_data["scoreboard-pushes"])
        damage_taken = int(player_data["scoreboard-destroyed"])
        win = 1 if "win" in player_data else 0

        damage_dealt = int(player_data["scoreboard-pushes"])
        return (
            (damage_dealt / damage_taken * (score + damage_dealt / 20) * time_factor)
            / 2.35
            + win * 300,
        )

    def medals_in_scoreboard_mid(self):
        return ["captures", "assists", "defends"]


class GametypeFT(AbstractGametype):
    def calc_player_perf(self, player_data, time_factor):
        damage_dealt = int(player_data["scoreboard-pushes"])
        frags_count = int(player_data["scoreboard-kills"])
        deaths_count = int(player_data["scoreboard-deaths"])
        assists_count = int(player_data["medal-assists"])

        damage_dealt = int(player_data["scoreboard-pushes"])
        return (
            damage_dealt / 100 + 0.5 * (frags_count - deaths_count) + 2 * assists_count
        ) * time_factor

    def medals_in_scoreboard_mid(self):
        return ["assists"]


class GametypeTDM(AbstractGametype):
    def calc_player_perf(self, player_data, time_factor):
        damage_dealt = int(player_data["scoreboard-pushes"])
        frags_count = int(player_data["scoreboard-kills"])
        deaths_count = int(player_data["scoreboard-deaths"])
        damage_taken = int(player_data["scoreboard-destroyed"])

        return (
            0.5 * (frags_count - deaths_count)
            + 0.004 * (damage_dealt - damage_taken)
            + 0.003 * damage_dealt
        ) * time_factor

    def extra_factor(self, matches, wins, losses):
        return 1 + (0.15 * (wins / matches - losses / matches))

    def medals_in_scoreboard_right(self):
        return ["excellent", "impressive"]


class GametypeTDM2V2(GametypeTDM):
    def force_by_match_report(self, data):
        return data["game_meta"]["G"] == "tdm" and len(data["players"]) == 4

    def override_min_player_count(self):
        return 4


GAMETYPE_RULES["ad"] = GametypeAD()
GAMETYPE_RULES["ca"] = GametypeCA()
GAMETYPE_RULES["ctf"] = GametypeCTF()
GAMETYPE_RULES["ft"] = GametypeFT()
GAMETYPE_RULES["tdm"] = GametypeTDM()
GAMETYPE_RULES["tdm2v2"] = GametypeTDM2V2()
