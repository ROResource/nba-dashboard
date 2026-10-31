import importlib.util
import datetime as dt
import copy
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
                 patch.object(update, "refresh_standings", return_value=["Standings offline"]), \
                 patch.object(update, "refresh_players", return_value=["Player offline"]), \
                 patch.object(update, "refresh_day", return_value=[]), \
                 patch.object(update, "read_feed", return_value=[]):
                self.assertEqual(update.run(args), 1)
            self.assertEqual(schedule.call_args.args[0],
                             dt.datetime.now(update.ZoneInfo("America/New_York")).date())
            index = update.load(Path(tmp) / "index.json")
            self.assertEqual(index["health"]["schedule"], "error")
            self.assertEqual(index["health"]["standings"], "error")
            self.assertEqual(index["health"]["players"], "error")
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


class TestStandings(unittest.TestCase):
    def data(self):
        conference = {"season": {"year": 2027, "displayName": "2026-27"}, "children": []}
        division = {"season": {"year": 2027}, "children": []}
        for conf in range(2):
            entries, groups = [], []
            for div in range(3):
                members = []
                for index in range(5):
                    rank = div * 5 + index + 1
                    wins, losses = 16 - rank, rank
                    stats = {"wins": wins, "losses": losses, "winPercent": wins / 16,
                             "playoffSeed": rank, "gamesBehind": rank - 1,
                             "avgPointsFor": 110, "avgPointsAgainst": 105, "differential": 5}
                    entry = {"team": {"id": str(conf * 15 + rank),
                                      "displayName": f"Team {conf}-{rank}", "abbreviation": f"T{rank}"},
                             "stats": [{"name": key, "value": value} for key, value in stats.items()]}
                    entries.append(entry)
                    members.append(copy.deepcopy(entry))
                groups.append({"id": f"{conf}-{div}", "name": f"Division {div}",
                               "standings": {"season": 2027, "seasonType": 2, "entries": members}})
            conference["children"].append({"id": str(conf), "name": f"Conference {conf}",
                                           "standings": {"season": 2027, "seasonType": 2, "entries": entries}})
            division["children"].append({"id": str(conf), "children": groups})
        return conference, division

    def test_build_complete_standings_and_optional_missing(self):
        result = update.build_standings(*self.data())
        self.assertEqual(len(result["teams"]), 30)
        self.assertEqual(len(result["divisions"]), 6)
        self.assertEqual(result["season"]["type"], 2)
        team = result["teams"][0]
        self.assertEqual(team["division_id"], "0-0")
        self.assertEqual(team["stats"]["conference_rank"], 1)
        self.assertIsNone(team["stats"]["last_ten"])
        self.assertEqual(team["stats"]["point_diff"], 5)

    def test_zero_metrics_are_not_missing(self):
        entry = self.data()[0]["children"][0]["standings"]["entries"][-1]
        entry["stats"].append({"name": "differential", "value": 0})
        self.assertEqual(update.standings_stats(entry)["point_diff"], 0)
        self.assertEqual(update.standings_stats(entry)["wins"], 1)

    def test_invalid_numeric_metrics(self):
        for value in (float("nan"), float("inf"), True, "12"):
            entry = copy.deepcopy(self.data()[0]["children"][0]["standings"]["entries"][0])
            entry["stats"].append({"name": "wins", "value": value})
            with self.assertRaises(ValueError):
                update.standings_stats(entry)

    def test_inconsistent_record_is_rejected(self):
        entry = self.data()[0]["children"][0]["standings"]["entries"][0]
        entry["stats"].append({"name": "winPercent", "value": 0})
        with self.assertRaises(ValueError):
            update.standings_stats(entry)

    def test_partial_and_mismatched_seasons_rejected(self):
        conf, div = self.data()
        div["season"]["year"] = 2026
        with self.assertRaises(ValueError):
            update.build_standings(conf, div)
        conf, div = self.data()
        conf["children"][0]["standings"]["entries"].pop()
        with self.assertRaises(ValueError):
            update.build_standings(conf, div)
        conf, div = self.data()
        div["children"][0]["children"][0]["standings"]["seasonType"] = 3
        with self.assertRaises(ValueError):
            update.build_standings(conf, div)

    def test_duplicate_ranks_and_memberships_rejected(self):
        conf, div = self.data()
        conf["children"][0]["standings"]["entries"][0]["stats"].append({"name": "playoffSeed", "value": 2})
        with self.assertRaises(ValueError):
            update.build_standings(conf, div)
        conf, div = self.data()
        div["children"][0]["children"][0]["standings"]["entries"][1] = copy.deepcopy(div["children"][0]["children"][0]["standings"]["entries"][0])
        with self.assertRaises(ValueError):
            update.build_standings(conf, div)

    def test_refresh_success_and_last_good_failure(self):
        with TemporaryDirectory() as tmp, patch.object(update, "DATA", Path(tmp)):
            with patch.object(update, "get", side_effect=list(self.data())) as get:
                self.assertEqual(update.refresh_standings(), [])
            self.assertEqual(get.call_count, 2)
            self.assertIn("season=2027", get.call_args.args[0])
            first = update.load(Path(tmp) / "standings.json")
            with patch.object(update, "get", side_effect=RuntimeError("offline")):
                self.assertTrue(update.refresh_standings())
            saved = update.load(Path(tmp) / "standings.json")
            self.assertEqual(saved["status"], "stale")
            self.assertEqual(saved["checked_at"], first["checked_at"])
            self.assertEqual(saved["teams"], first["teams"])

    def test_first_failure_is_unavailable_not_empty_league(self):
        with TemporaryDirectory() as tmp, patch.object(update, "DATA", Path(tmp)):
            with patch.object(update, "get", return_value={}):
                self.assertTrue(update.refresh_standings())
            saved = update.load(Path(tmp) / "standings.json")
            self.assertEqual(saved["status"], "unavailable")
            self.assertIsNone(saved["checked_at"])


class TestPlayerSeasons(unittest.TestCase):
    def payload(self, year=2027, phase=2, gp="5"):
        return {"categories": [{
            "displayName": "Postseason Averages" if phase == 3 else "Regular Season Averages",
            "names": ["gamesPlayed", "avgMinutes", "avgPoints", "avgRebounds", "avgAssists",
                      "avgSteals", "avgBlocks", "avgTurnovers", "fieldGoalPct",
                      "threePointFieldGoalPct", "freeThrowPct"],
            "statistics": [{"season": {"year": year}, "teamId": "2", "teamSlug": "team",
                            "stats": [gp, "32.1", "24.2", "7.0", "4.3", "0.0", "1.0", "2.1",
                                      "46.4", "0.0", "88.9"]}]}]}

    def target(self):
        return {"year": 2027, "type": 2, "id": "1", "name": "Example Player",
                "through": "2026-10-30", "played": {"g1": "2026-10-30"}}

    def days(self):
        player = {"id": "1", "name": "Example Player", "dnp": False, "stats": {"MIN": "20"}}
        return [{"date": "2026-10-30", "games": [{
            "id": "g1", "season_year": 2027, "season_type": 2,
            "away": {"players": [player]}, "home": {"players": []}}]}]

    def test_player_season_values_and_percent_scale(self):
        stats = update.player_season_stats(self.payload(), 2027, 2)
        self.assertEqual(stats["gp"], 5)
        self.assertEqual(stats["fg_pct"], 46.4)
        self.assertEqual(stats["three_pct"], 0)
        self.assertEqual(stats["spg"], 0)
        self.assertEqual(stats["ppg"], 24.2)

    def test_wrong_year_and_empty_nba_are_not_career_stats(self):
        self.assertIsNone(update.player_season_stats(self.payload(year=2026), 2027, 2))
        self.assertIsNone(update.player_season_stats({"categories": []}, 2027, 2))
        self.assertIsNone(update.player_season_stats(
            {"filters": [{"name": "league", "value": "nba"}]}, 2027, 2))
        with self.assertRaises(ValueError):
            update.player_season_stats({}, 2027, 2)

    def test_regular_and_postseason_do_not_mix(self):
        self.assertEqual(update.player_season_stats(self.payload(phase=3), 2027, 3)["gp"], 5)
        with self.assertRaises(ValueError):
            update.player_season_stats(self.payload(phase=3), 2027, 2)

    def test_traded_player_uses_combined_not_last_team(self):
        payload = self.payload(gp="3")
        cat = payload["categories"][0]
        second = copy.deepcopy(cat["statistics"][0])
        second["teamId"] = "3"
        second["stats"][0] = "2"
        combined = copy.deepcopy(second)
        combined.pop("teamId")
        combined["teamSlug"] = "2026-27 Totals"
        combined["stats"][0] = "5"
        combined["stats"][2] = "21.7"
        cat["statistics"] += [second, combined]
        stats = update.player_season_stats(payload, 2027, 2)
        self.assertEqual(stats["gp"], 5)
        self.assertEqual(stats["ppg"], 21.7)
        cat["statistics"].pop()
        with self.assertRaises(ValueError):
            update.player_season_stats(payload, 2027, 2)

    def test_missing_optional_stats_and_zero_games(self):
        payload = self.payload()
        payload["categories"][0]["statistics"][0]["stats"][8] = "--"
        self.assertIsNone(update.player_season_stats(payload, 2027, 2)["fg_pct"])
        self.assertIsNone(update.player_season_stats(self.payload(gp="0"), 2027, 2))

    def test_invalid_metrics_and_wrong_label_count(self):
        for value in ("NaN", "inf", "-1", True):
            payload = self.payload()
            payload["categories"][0]["statistics"][0]["stats"][2] = value
            with self.assertRaises(ValueError):
                update.player_season_stats(payload, 2027, 2)
        payload = self.payload()
        payload["categories"][0]["statistics"][0]["stats"][8] = "101"
        with self.assertRaises(ValueError):
            update.player_season_stats(payload, 2027, 2)
        payload["categories"][0]["statistics"][0]["stats"].pop()
        with self.assertRaises(ValueError):
            update.player_season_stats(payload, 2027, 2)

    def test_targets_deduplicate_games_and_separate_competitions(self):
        days = self.days()
        days[0]["games"].append(copy.deepcopy(days[0]["games"][0]))
        targets = list(update.player_targets(days))
        self.assertEqual(len(targets), 1)
        self.assertEqual(len(targets[0]["played"]), 1)
        playoff = copy.deepcopy(days[0])
        playoff["games"][0]["season_type"] = 3
        playoff["games"] = playoff["games"][:1]
        self.assertEqual(len(list(update.player_targets(days + [playoff]))), 2)

    def test_dnp_and_preseason_do_not_increment_regular_gp(self):
        days = self.days()
        days[0]["games"][0]["away"]["players"][0]["dnp"] = True
        self.assertEqual(list(update.player_targets(days))[0]["played"], {})
        days[0]["games"][0]["away"]["players"][0]["dnp"] = False
        days[0]["games"][0]["season_type"] = 1
        self.assertEqual(list(update.player_targets(days))[0]["played"], {})

    def test_success_then_failure_preserves_observation_and_averages(self):
        with TemporaryDirectory() as tmp, patch.object(update, "DATA", Path(tmp)):
            with patch.object(update, "get", return_value=self.payload()):
                self.assertIsNone(update.refresh_player(self.target()))
            path = update.player_season_path(2027, 2, "1")
            first = update.load(path)
            with patch.object(update, "get", side_effect=RuntimeError("offline")):
                self.assertTrue(update.refresh_player(self.target()))
            saved = update.load(path)
            self.assertEqual(saved["status"], "stale")
            self.assertEqual(saved["checked_at"], first["checked_at"])
            self.assertEqual(saved["stats"], first["stats"])

    def test_gp_lag_does_not_replace_last_good(self):
        with TemporaryDirectory() as tmp, patch.object(update, "DATA", Path(tmp)):
            with patch.object(update, "get", return_value=self.payload()):
                update.refresh_player(self.target())
                target = self.target()
                target["played"]["g2"] = "2026-10-31"
                target["through"] = "2026-10-31"
                self.assertIn("caught up", update.refresh_player(target))
            saved = update.load(update.player_season_path(2027, 2, "1"))
            self.assertEqual(saved["status"], "stale")
            self.assertEqual(saved["stats"]["gp"], 5)
            self.assertEqual(saved["archive_through"], "2026-10-30")

    def test_no_published_stats_is_distinct_from_failed_request(self):
        with TemporaryDirectory() as tmp, patch.object(update, "DATA", Path(tmp)):
            target = self.target()
            with patch.object(update, "get", return_value={"categories": []}):
                self.assertIsNone(update.refresh_player(target))
            self.assertEqual(update.load(update.player_season_path(2027, 2, "1"))["status"], "no_stats")
            with patch.object(update, "get", return_value={}):
                self.assertTrue(update.refresh_player(target))
            self.assertEqual(update.load(update.player_season_path(2027, 2, "1"))["status"], "unavailable")

    def test_valid_empty_response_does_not_erase_published_averages(self):
        with TemporaryDirectory() as tmp, patch.object(update, "DATA", Path(tmp)):
            with patch.object(update, "get", return_value=self.payload()):
                update.refresh_player(self.target())
            with patch.object(update, "get", return_value={"categories": []}):
                self.assertIn("empty", update.refresh_player(self.target()))
            saved = update.load(update.player_season_path(2027, 2, "1"))
            self.assertEqual(saved["status"], "stale")
            self.assertEqual(saved["stats"]["gp"], 5)
    def test_fresh_snapshots_skip_network_and_new_game_refreshes(self):
        with TemporaryDirectory() as tmp, patch.object(update, "DATA", Path(tmp)):
            with patch.object(update, "get", return_value=self.payload()):
                update.refresh_player(self.target())
            with patch.object(update, "get") as get:
                self.assertEqual(update.refresh_players(self.days()), [])
                get.assert_not_called()
            days = self.days()
            extra = copy.deepcopy(days[0])
            extra["date"] = "2026-10-31"
            extra["games"][0]["id"] = "g2"
            with patch.object(update, "get", return_value=self.payload(gp="6")) as get:
                self.assertEqual(update.refresh_players(days + [extra]), [])
                self.assertEqual(get.call_count, 1)

    def test_weekly_correction_pass_and_distinct_file_paths(self):
        with TemporaryDirectory() as tmp, patch.object(update, "DATA", Path(tmp)):
            with patch.object(update, "now", return_value="2026-10-20T10:00:00+00:00"), \
                 patch.object(update, "get", return_value=self.payload()):
                update.refresh_player(self.target())
            with patch.object(update, "now", return_value="2026-10-31T10:00:00+00:00"), \
                 patch.object(update, "get", return_value=self.payload()) as get:
                self.assertEqual(update.refresh_players(self.days()), [])
                self.assertEqual(get.call_count, 1)
            self.assertNotEqual(update.player_season_path(2027, 2, "1"),
                                update.player_season_path(2027, 3, "1"))
            self.assertNotEqual(update.player_season_path(2027, 2, "1"),
                                update.player_season_path(2026, 2, "1"))

    def test_stale_new_appearance_honors_retry_cooldown_and_health(self):
        with TemporaryDirectory() as tmp, patch.object(update, "DATA", Path(tmp)):
            with patch.object(update, "get", return_value=self.payload()):
                update.refresh_player(self.target())
            days = self.days()
            days[0]["date"] = "2026-10-31"
            days[0]["games"][0]["id"] = "g2"
            with patch.object(update, "get", side_effect=RuntimeError("offline")):
                self.assertTrue(update.refresh_players(days))
            with patch.object(update, "get") as get:
                self.assertTrue(update.refresh_players(days))
                get.assert_not_called()

    def test_refresh_budget_defers_requests_but_keeps_valid_placeholder(self):
        with TemporaryDirectory() as tmp, patch.object(update, "DATA", Path(tmp)):
            with patch.object(update, "PLAYER_REFRESH_SECONDS", -1), patch.object(update, "get") as get:
                failures = update.refresh_players(self.days())
                get.assert_not_called()
            self.assertIn("budget", failures[0])
            self.assertEqual(update.load(update.player_season_path(2027, 2, "1"))["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
