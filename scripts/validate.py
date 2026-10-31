"""Validate cross-file archive integrity before publishing."""
import json
import re
import datetime as dt
import math
from update import player_targets, player_season_path
from pathlib import Path

data = Path(__file__).resolve().parents[1] / "site" / "data"
index = json.loads((data / "index.json").read_text())
assert index["days"], "No archived days"
dates = [day["date"] for day in index["days"]]
assert dates == sorted(set(dates), reverse=True), "Dates must be unique and newest first"
games = 0
for entry in index["days"]:
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry["date"])
    day = json.loads((data / "days" / f"{entry['date']}.json").read_text())
    assert day["date"] == entry["date"]
    assert len(day["games"]) == entry["games"]
    assert len({g["id"] for g in day["games"]}) == len(day["games"])
    for game in day["games"]:
        assert game["source"].startswith("https://www.espn.com/")
        for side in ("away", "home"):
            team = game[side]
            assert isinstance(team["score"], int)
            assert isinstance(team["players"], list)
            if team["periods"]:
                assert sum(team["periods"]) == team["score"], f"Period mismatch: {game['id']}"
        games += 1
    for kind, video in day["videos"].items():
        assert kind in ("top_plays", "recap")
        assert video["channel_id"] == "UCWJ2lWNubArHWmf3FIHbfcQ"
        assert video["date"] == day["date"]
        assert re.fullmatch(r"[\w-]{11}", video["id"])
        assert all(c["seconds"] >= 0 for c in video["chapters"])
print(f"Validated {len(dates)} archive dates and {games} completed games.")

schedule = json.loads((data / "schedule.json").read_text())
assert schedule["schema_version"] == 1
assert schedule["game_date_timezone"] == "America/New_York"
assert schedule["source"] == "https://www.espn.com/nba/schedule"
dt.datetime.fromisoformat(schedule["generated_at"])
start = dt.date.fromisoformat(schedule["from_date"])
assert len(schedule["days"]) == 8, "Schedule must include today plus seven days"
assert schedule["through_date"] == (start + dt.timedelta(days=7)).isoformat()
for offset, day in enumerate(schedule["days"]):
    assert day["date"] == (start + dt.timedelta(days=offset)).isoformat()
    assert day["status"] in ("ok", "stale", "unavailable")
    if day["status"] == "unavailable":
        assert day["games"] is None
        continue
    assert isinstance(day["games"], list)
    assert day["checked_at"], "Available fixtures must have an observation time"
    assert len({g["id"] for g in day["games"]}) == len(day["games"])
    for game in day["games"]:
        assert dt.datetime.fromisoformat(game["start_time"].replace("Z", "+00:00")).tzinfo
        assert isinstance(game["completed"], bool)
        assert isinstance(game["time_tbd"], bool)
        assert game["state"] in ("pre", "in", "post")
        for side in ("away", "home"):
            assert game[side]["id"] and game[side]["name"]
            assert "score" not in game[side], "Schedule must not expose scores"
print("Validated eight schedule dates, including explicit fallback states.")

standings = json.loads((data / "standings.json").read_text())
assert standings["schema_version"] == 1
assert standings["status"] in ("ok", "stale", "unavailable")
assert standings["source"] == "https://www.espn.com/nba/standings"
dt.datetime.fromisoformat(standings["generated_at"])
if standings["status"] == "unavailable":
    assert standings["teams"] == [] and standings["checked_at"] is None
else:
    assert standings["season"]["type"] == 2
    assert standings["season"]["label"]
    dt.datetime.fromisoformat(standings["checked_at"])
    conferences = {g["id"] for g in standings["conferences"]}
    divisions = {g["id"]: g["conference_id"] for g in standings["divisions"]}
    assert len(standings["conferences"]) == len(conferences) == 2
    assert len(standings["divisions"]) == len(divisions) == 6
    assert len(standings["teams"]) == len({t["id"] for t in standings["teams"]}) == 30
    for conf in conferences:
        group = [t for t in standings["teams"] if t["conference_id"] == conf]
        assert len(group) == 15
        assert sorted(t["stats"]["conference_rank"] for t in group) == list(range(1, 16))
    for division, conf in divisions.items():
        assert conf in conferences
        assert len([t for t in standings["teams"] if t["division_id"] == division]) == 5
    for team in standings["teams"]:
        assert team["name"] and team["abbreviation"]
        assert divisions[team["division_id"]] == team["conference_id"]
        stats = team["stats"]
        assert isinstance(stats["wins"], int) and stats["wins"] >= 0
        assert isinstance(stats["losses"], int) and stats["losses"] >= 0
        assert 0 <= stats["win_pct"] <= 1
        if stats["wins"] + stats["losses"]:
            assert abs(stats["win_pct"] - stats["wins"] / (stats["wins"] + stats["losses"])) <= .001
        for key in ("points_for", "points_against", "point_diff", "conference_gb"):
            assert stats[key] is None or (isinstance(stats[key], (int, float)) and math.isfinite(stats[key]))
        if all(stats[key] is not None for key in ("points_for", "points_against", "point_diff")):
            assert abs(stats["points_for"] - stats["points_against"] - stats["point_diff"]) <= .21
print(f"Validated standings snapshot: {standings['status']}.")

player_count = 0
player_statuses = {}
targets = list(player_targets([json.loads(p.read_text()) for p in sorted((data / "days").glob("*.json"))]))
for target in targets:
    path = player_season_path(target["year"], target["type"], target["id"])
    player = json.loads(path.read_text())
    assert player["schema_version"] == 1 and player["id"] == target["id"]
    assert player["season"] == {"year": target["year"],
                                "label": f"{target['year'] - 1}-{str(target['year'])[-2:]}",
                                "type": target["type"]}
    assert player["scope"] == "all_teams"
    assert player["source"] == f"https://www.espn.com/nba/player/stats/_/id/{target['id']}"
    assert player["status"] in ("ok", "stale", "no_stats", "unavailable")
    dt.datetime.fromisoformat(player["generated_at"])
    dt.date.fromisoformat(player["archive_through"])
    assert isinstance(player["archive_gp"], int) and player["archive_gp"] >= 0
    if player["status"] in ("ok", "stale"):
        dt.datetime.fromisoformat(player["checked_at"])
        stats = player["stats"]
        assert isinstance(stats["gp"], int) and stats["gp"] > 0
        for key in ("mpg", "ppg", "rpg", "apg", "spg", "bpg", "tov", "fg_pct", "three_pct", "ft_pct"):
            value = stats[key]
            assert value is None or (isinstance(value, (int, float)) and math.isfinite(value) and value >= 0)
            if key.endswith("_pct") and value is not None:
                assert value <= 100, "Shooting percentages use a 0-100 scale"
    else:
        assert player["stats"] is None
    player_count += 1
    player_statuses[player["status"]] = player_statuses.get(player["status"], 0) + 1
print(f"Validated {player_count} player-season snapshots: {player_statuses}.")
