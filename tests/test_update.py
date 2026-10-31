import importlib.util
import datetime as dt
import unittest
from pathlib import Path
from unittest.mock import patch
from tempfile import TemporaryDirectory
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location("update", Path(__file__).resolve().parents[1] / "scripts/update.py")
update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update)


class TestUpdate(unittest.TestCase):
    def fixture(self, **status):
        return {"id": "fixture-1", "date": "2026-11-01T00:30Z",
                "status": {"type": {"state": "pre", "name": "STATUS_SCHEDULED",
                                    "description": "Scheduled", **status}},
                "competitions": [{"competitors": [
                    {"homeAway": side, "score": "99",
                     "team": {"id": side, "displayName": side.title(), "abbreviation": side[:1]}}
                    for side in ("away", "home")]}]}

    def test_schedule_fixture_strips_scores_and_keeps_utc(self):
        game = update.schedule_game(self.fixture())
        self.assertEqual(game["start_time"], "2026-11-01T00:30Z")
        self.assertNotIn("score", game["home"])
        self.assertFalse(game["completed"])
        self.assertEqual(update.schedule_game(self.fixture(completed=True, state="post"))["state"], "post")

    def test_schedule_today_and_seven_days_cross_month(self):
        with TemporaryDirectory() as tmp, patch.object(update, "DATA", Path(tmp)):
            with patch.object(update, "get", return_value={"events": []}) as get:
                self.assertEqual(update.refresh_schedule(dt.date(2026, 10, 31)), [])
            schedule = update.load(Path(tmp) / "schedule.json")
            self.assertEqual(len(schedule["days"]), 8)
            self.assertEqual(schedule["through_date"], "2026-11-07")
            self.assertEqual(schedule["days"][0]["games"], [])
            self.assertEqual(get.call_count, 8)
            self.assertIn("dates=20261107", get.call_args.args[0])

    def test_schedule_partial_failure_preserves_only_matching_dates(self):
        with TemporaryDirectory() as tmp, patch.object(update, "DATA", Path(tmp)):
            old = {"days": [{"date": "2026-10-31", "games": [update.schedule_game(self.fixture())],
                             "checked_at": "2026-10-30T10:00:00Z"},
                            {"date": "2026-10-30", "games": [], "checked_at": "old"}]}
            update.save(Path(tmp) / "schedule.json", old)
            with patch.object(update, "get", side_effect=RuntimeError("offline")):
                self.assertEqual(len(update.refresh_schedule(dt.date(2026, 10, 31))), 8)
            schedule = update.load(Path(tmp) / "schedule.json")
            self.assertEqual(schedule["days"][0]["status"], "stale")
            self.assertEqual(schedule["days"][0]["checked_at"], "2026-10-30T10:00:00Z")
            self.assertEqual(schedule["days"][0]["games"][0]["id"], "fixture-1")
            self.assertIsNone(schedule["days"][1]["games"])
            self.assertEqual(schedule["days"][1]["status"], "unavailable")
            self.assertNotIn("2026-10-30", [d["date"] for d in schedule["days"]])

    def test_schedule_bad_schema_is_not_a_no_game_day(self):
        with TemporaryDirectory() as tmp, patch.object(update, "DATA", Path(tmp)):
            with patch.object(update, "get", return_value={}):
                self.assertEqual(len(update.refresh_schedule(dt.date(2026, 10, 31))), 8)
            self.assertIsNone(update.load(Path(tmp) / "schedule.json")["days"][0]["games"])

    def test_schedule_rejects_invalid_start_and_handles_tbd(self):
        event = self.fixture()
        event["competitions"][0]["timeValid"] = False
        self.assertTrue(update.schedule_game(event)["time_tbd"])
        event["date"] = "not-a-date"
        with self.assertRaises(ValueError):
            update.schedule_game(event)

    def test_schedule_unexpected_empty_retains_saved_games(self):
        with TemporaryDirectory() as tmp, patch.object(update, "DATA", Path(tmp)):
            with patch.object(update, "get", return_value={"events": [self.fixture()]}):
                update.refresh_schedule(dt.date(2026, 10, 31))
            with patch.object(update, "get", return_value={"events": []}):
                self.assertEqual(len(update.refresh_schedule(dt.date(2026, 10, 31))), 8)
            self.assertEqual(update.load(Path(tmp) / "schedule.json")["days"][0]["status"], "stale")

    def test_backfill_schedule_still_uses_today_and_reports_failure(self):
        with TemporaryDirectory() as tmp, patch.object(update, "DATA", Path(tmp)):
            update.save(Path(tmp) / "days/2026-10-20.json",
                        {"date": "2026-10-20", "games": [], "videos": {}})
            args = SimpleNamespace(from_date="2026-10-20", to_date="2026-10-20",
                                   days=7, skip_discovery=True, video_limit=20)
            with patch.object(update, "refresh_schedule", return_value=["Schedule offline"]) as schedule, \
                 patch.object(update, "refresh_day", return_value=[]), \
                 patch.object(update, "read_feed", return_value=[]):
                self.assertEqual(update.run(args), 1)
            self.assertEqual(schedule.call_args.args[0],
                             dt.datetime.now(update.ZoneInfo("America/New_York")).date())
            index = update.load(Path(tmp) / "index.json")
            self.assertEqual(index["health"]["schedule"], "error")
            self.assertEqual(index["health"]["scores"], "ok")
            self.assertEqual(index["health"]["videos"], "ok")
            self.assertEqual(index["days"][0]["date"], "2026-10-20")

    def test_schedule_year_rollover_and_dst_instants(self):
        event = self.fixture()
        game = update.schedule_game(event)
        instant = dt.datetime.fromisoformat(game["start_time"].replace("Z", "+00:00"))
        self.assertEqual(instant.astimezone(update.ZoneInfo("Europe/Dublin")).day, 1)
        self.assertEqual(instant.astimezone(update.ZoneInfo("America/New_York")).day, 31)
        with TemporaryDirectory() as tmp, patch.object(update, "DATA", Path(tmp)):
            with patch.object(update, "get", return_value={"events": []}):
                update.refresh_schedule(dt.date(2026, 12, 29))
            self.assertEqual(update.load(Path(tmp) / "schedule.json")["through_date"], "2027-01-05")

    def test_title_dates_use_game_date(self):
        self.assertEqual(update.title_date("NBA's Top 5 Plays of the Night | October 24, 2026"), "2026-10-24")
        self.assertIsNone(update.title_date("Top 10 plays of the season"))

    def test_video_matching(self):
        self.assertEqual(update.video_kind("NBA’s Top 10 Plays of the Night"), "top_plays")
        self.assertEqual(update.video_kind("NBA's Top 5 Plays"), "top_plays")
        self.assertEqual(update.video_kind("NBA’s Nightly Recap"), "recap")
        self.assertIsNone(update.video_kind("Top 10 dunks this season"))

    def test_chapters(self):
        c = update.chapters("0:00 Wizards at Bulls\n2:37 Heat at Hornets\n1:02:03 Final game\n20:52...\nSubscribe now")
        self.assertEqual([x["seconds"] for x in c], [0, 157, 3723])
        self.assertEqual(c[1]["label"], "Heat at Hornets")

    def test_boxscore_labels_not_positions(self):
        box = update.boxscore({"boxscore":{"players":[{"team":{"id":"1"}, "statistics":[{
            "labels":["REB","PTS","MIN"],"totals":["45","110",""],
            "athletes":[{"athlete":{"id":"7","displayName":"Test Player"}, "starter":True,
                         "stats":["8","22","30"]}]}]}]}})
        self.assertEqual(box["1"]["players"][0]["stats"]["PTS"], "22")
        self.assertEqual(box["1"]["totals"]["REB"], "45")

    def test_invalid_video_id(self):
        with self.assertRaises(ValueError):
            update.video_record('"><script>', "NBA Nightly Recap")

    def test_feed_channel_without_uc_prefix(self):
        feed = f'<feed xmlns="{update.NS["a"]}" xmlns:yt="{update.NS["yt"]}"><yt:channelId>{update.CHANNEL[2:]}</yt:channelId></feed>'
        with patch.object(update, "get", return_value=feed):
            self.assertEqual(update.read_feed(), [])

    def test_new_youtube_description_format(self):
        page = ('var ytInitialPlayerResponse = {"playabilityStatus":{"status":"LOGIN_REQUIRED"}};'
                'var ytInitialData = {"contents":{"videoSecondaryInfoRenderer":'
                '{"attributedDescription":{"content":"0:00 Wizards at Bulls\\n2:37 Heat at Hornets"}}}};')
        video=update.video_record("7GbdkPD3oRQ", "NBA Nightly Recap | October 24, 2026")
        with patch.object(update, "get", return_value=page):
            self.assertEqual(update.enrich_recap(video)["chapters"][1]["seconds"],157)

    def test_empty_response_preserves_archive(self):
        with TemporaryDirectory() as tmp, patch.object(update, "DATA", Path(tmp)):
            original={"date":"2026-10-24","games":[{"id":"saved"}],"videos":{}}
            update.save(Path(tmp)/"days/2026-10-24.json",original)
            with patch.object(update,"get",return_value={"events":[]}):
                update.refresh_day("2026-10-24")
            saved=update.load(Path(tmp)/"days/2026-10-24.json")
            self.assertEqual(saved["games"], [{"id":"saved"}])


if __name__ == "__main__":
    unittest.main()
