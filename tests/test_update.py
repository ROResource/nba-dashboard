import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch
from tempfile import TemporaryDirectory

spec = importlib.util.spec_from_file_location("update", Path(__file__).resolve().parents[1] / "scripts/update.py")
update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update)


class TestUpdate(unittest.TestCase):
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
