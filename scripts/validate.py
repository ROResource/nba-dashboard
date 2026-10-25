"""Validate cross-file archive integrity before publishing."""
import json
import re
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
