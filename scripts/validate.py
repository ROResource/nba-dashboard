"""Validate cross-file archive integrity before publishing."""
import json
import re
import datetime as dt
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
