#!/usr/bin/env python3
"""Build a durable, static NBA archive. No credentials or live browser requests."""
import argparse
import copy
import datetime as dt
import json
import logging
import re
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "site" / "data"
CHANNEL = "UCWJ2lWNubArHWmf3FIHbfcQ"
FEED = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL}"
API = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
LOG = logging.getLogger("update")
NS = {"a": "http://www.w3.org/2005/Atom",
      "yt": "http://www.youtube.com/xml/schemas/2015",
      "m": "http://search.yahoo.com/mrss/"}


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def get(url, json_data=True):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; NBA-Daily-Personal-Dashboard/1.0)",
                "Accept-Language": "en-US,en;q=0.9"})
            with urllib.request.urlopen(req, timeout=25) as response:
                value = response.read().decode("utf-8")
            return json.loads(value) if json_data else value
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def load(path, default=None):
    return json.loads(path.read_text()) if path.exists() else copy.deepcopy(default)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
    tmp.replace(path)


def title_date(title):
    match = re.search(r"([A-Z][a-z]+ \d{1,2},? \d{4})", title)
    if match:
        try:
            return dt.datetime.strptime(match[1].replace(",", ""), "%B %d %Y").date().isoformat()
        except ValueError:
            pass
    return None


def video_kind(title):
    if re.search(r"\btop\s*(?:10|5)\s+plays\b", title, re.I):
        return "top_plays"
    if re.search(r"\bnightly\s+recap\b", title, re.I):
        return "recap"
    return None


def chapters(description):
    result = []
    for line in description.splitlines():
        match = re.match(r"^\s*(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+?)\s*$", line)
        if match and not match[2].endswith(("...", "…")):
            parts = list(map(int, match[1].split(":")))
            seconds = sum(p * 60 ** i for i, p in enumerate(reversed(parts)))
            result.append({"label": match[2], "time": match[1], "seconds": seconds})
    return result


def video_record(video_id, title, description="", published=None):
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ValueError("Invalid YouTube video ID")
    return {"id": video_id, "title": title, "date": title_date(title),
            "kind": video_kind(title), "published": published,
            "source": f"https://www.youtube.com/watch?v={video_id}",
            "channel_id": CHANNEL, "chapters": chapters(description)}


def read_feed():
    root = ET.fromstring(get(FEED, False))
    # Atom feeds sometimes omit YouTube's "UC" channel prefix.
    if root.findtext("yt:channelId", namespaces=NS) not in (CHANNEL, CHANNEL[2:]):
        raise ValueError("Unexpected channel in NBA feed")
    return [video_record(e.findtext("yt:videoId", namespaces=NS),
                         e.findtext("a:title", "", NS),
                         e.findtext("m:group/m:description", "", NS),
                         e.findtext("a:published", namespaces=NS))
            for e in root.findall("a:entry", NS)]


def discover_videos(limit):
    """Official channel searches cover uploads that have fallen out of RSS."""
    result = []
    for query in ("nightly%20recap", "top%20plays"):
        process = subprocess.run(
            [sys.executable, "-m", "yt_dlp", "--flat-playlist", "--playlist-end",
             str(limit), "--dump-json", "--skip-download", "--no-warnings",
             "--socket-timeout", "20", "--retries", "2",
             f"https://www.youtube.com/@NBA/search?query={query}"],
            capture_output=True, text=True, timeout=180)
        if process.returncode:
            LOG.warning("Channel discovery: %s", process.stderr[-400:])
        for line in process.stdout.splitlines():
            v = json.loads(line)
            if v.get("channel_id") == CHANNEL:
                result.append(video_record(v["id"], v.get("title", ""),
                                           v.get("description") or ""))
    return result


def enrich_recap(video):
    """Read only public metadata; never download video/audio."""
    page = get(video["source"], False)
    marker = re.search(r"(?:var\s+)?ytInitialPlayerResponse\s*=\s*", page)
    if marker:
        player, _ = json.JSONDecoder().raw_decode(page[marker.end():])
        details = player.get("videoDetails", {})
        if not details:
            # Bot/login walls may omit player metadata but leave public
            # descriptions in the page's videoSecondaryInfoRenderer.
            data_marker = re.search(r"(?:var\s+)?ytInitialData\s*=\s*", page)
            if data_marker:
                data, _ = json.JSONDecoder().raw_decode(page[data_marker.end():])
                stack = [data]
                while stack:
                    node = stack.pop()
                    if isinstance(node, dict):
                        renderer = node.get("videoSecondaryInfoRenderer", {})
                        runs = renderer.get("description", {}).get("runs", [])
                        description = renderer.get("attributedDescription", {}).get("content", "")
                        if not description:
                            description = "".join(r.get("text", "") for r in runs)
                        found = chapters(description)
                        if found:
                            video["chapters"] = found
                            video["metadata_enriched"] = True
                            return video
                        stack.extend(node.values())
                    elif isinstance(node, list):
                        stack.extend(node)
            return video
        if details.get("channelId") != CHANNEL:
            raise ValueError("Unexpected video channel")
        found = chapters(details.get("shortDescription", ""))
        if found:
            video["chapters"] = found
        video["duration_seconds"] = int(details.get("lengthSeconds", 0))
    return video


def team_record(competitor):
    t = competitor["team"]
    return {"id": str(t["id"]), "name": t["displayName"],
            "short_name": t.get("name", t["displayName"]),
            "abbreviation": t["abbreviation"], "logo": t.get("logo", ""),
            "score": int(competitor["score"]),
            "periods": [int(p["value"]) for p in competitor.get("linescores", [])],
            "record": next((r["summary"] for r in competitor.get("records", [])
                            if r.get("type") == "total"), ""),
            "players": [], "totals": {}}


def boxscore(summary):
    result = {}
    for team in summary.get("boxscore", {}).get("players", []):
        players, totals = [], {}
        for group in team.get("statistics", []):
            labels = group.get("labels", [])
            totals.update(dict(zip(labels, group.get("totals", []))))
            for item in group.get("athletes", []):
                athlete = item.get("athlete", {})
                players.append({
                    "id": str(athlete["id"]), "name": athlete["displayName"],
                    "short_name": athlete.get("shortName", athlete["displayName"]),
                    "starter": bool(item.get("starter")), "dnp": bool(item.get("didNotPlay")),
                    "reason": item.get("reason", ""),
                    "stats": dict(zip(labels, item.get("stats", [])))})
        result[str(team["team"]["id"])] = {"players": players, "totals": totals}
    return result


def refresh_day(day, force=False):
    path = DATA / "days" / f"{day}.json"
    old = load(path, {"date": day, "games": [], "videos": {}})
    board = get(f"{API}/scoreboard?dates={day.replace('-', '')}&limit=100")
    if not isinstance(board.get("events"), list):
        raise ValueError("Scoreboard is missing its events array")
    old_games = {g["id"]: g for g in old.get("games", [])}
    games, failures = [], []
    for event in board["events"]:
        if not event.get("status", {}).get("type", {}).get("completed"):
            continue
        competition = event["competitions"][0]
        competitors = {c["homeAway"]: c for c in competition["competitors"]}
        game = {"id": event["id"], "name": event["name"],
                "status": event["status"]["type"].get("shortDetail", "Final"),
                "source": f"https://www.espn.com/nba/boxscore/_/gameId/{event['id']}",
                "observed_at": now(),
                "away": team_record(competitors["away"]),
                "home": team_record(competitors["home"])}
        previous = old_games.get(game["id"])
        complete = previous and all(previous[s].get("players") for s in ("away", "home"))
        # Recheck yesterday/recent corrections even when archived.
        if complete and not force:
            for side in ("away", "home"):
                game[side].update({k: previous[side][k] for k in ("players", "totals")})
        else:
            try:
                boxes = boxscore(get(f"{API}/summary?event={game['id']}"))
                for side in ("away", "home"):
                    if not boxes.get(game[side]["id"], {}).get("players"):
                        raise ValueError("Player box score not available yet")
                    game[side].update(boxes[game[side]["id"]])
            except Exception as exc:
                failures.append(f"{day} {game['id']}: {exc}")
                if complete:
                    for side in ("away", "home"):
                        game[side].update({k: previous[side][k] for k in ("players", "totals")})
                else:
                    game["boxscore_status"] = "pending"
        games.append(game)
    # Preserve already archived finals if a temporary empty response arrives.
    merged = {g["id"]: g for g in old.get("games", [])}
    merged.update({g["id"]: g for g in games})
    old.update({"games": list(merged.values()), "scores_checked_at": now(),
                "scheduled_games": len(board["events"]),
                "pending_games": sum(not e.get("status", {}).get("type", {}).get("completed")
                                     for e in board["events"])})
    save(path, old)
    return failures


def schedule_game(event):
    """Keep only fixture metadata; never publish live scores in this panel."""
    competition = event["competitions"][0]
    competitors = {c["homeAway"]: c["team"] for c in competition["competitors"]}
    status = event["status"]["type"]
    start = event.get("date") or competition.get("date")
    if not start or dt.datetime.fromisoformat(start.replace("Z", "+00:00")).tzinfo is None:
        raise ValueError("Fixture start time must include a timezone")
    return {
        "id": str(event["id"]), "start_time": start,
        "time_tbd": bool(competition.get("timeValid") is False or
                         status.get("name") == "STATUS_TIME_TBD"),
        "state": status.get("state", "pre"),
        "status_name": status.get("name", ""),
        "status": status.get("description", "Scheduled"),
        "completed": bool(status.get("completed")),
        **{side: {"id": str(competitors[side]["id"]),
                  "name": competitors[side]["displayName"],
                  "abbreviation": competitors[side].get("abbreviation", "")}
           for side in ("away", "home")}}


def refresh_schedule(today):
    """Today plus seven days, with independent last-good fallback per date."""
    previous = load(DATA / "schedule.json", {})
    saved_days = {d["date"]: d for d in previous.get("days", [])}
    days, failures = [], []
    for offset in range(8):
        date = (today + dt.timedelta(days=offset)).isoformat()
        previous_day = saved_days.get(date, {})
        try:
            board = get(f"{API}/scoreboard?dates={date.replace('-', '')}&limit=100")
            if not isinstance(board.get("events"), list):
                raise ValueError("Scoreboard is missing its events array")
            games = [schedule_game(event) for event in board["events"]]
            if len({g["id"] for g in games}) != len(games):
                raise ValueError("Duplicate fixture IDs")
            if not games and previous_day.get("games"):
                raise ValueError("Unexpected empty response; keeping saved fixtures")
            days.append({"date": date, "checked_at": now(), "status": "ok",
                         "games": sorted(games, key=lambda g: (g["start_time"], g["id"]))})
        except Exception as exc:
            failures.append(f"Schedule {date}: {exc}")
            has_saved = isinstance(previous_day.get("games"), list)
            days.append({"date": date, "checked_at": previous_day.get("checked_at"),
                         "status": "stale" if has_saved else "unavailable",
                         "games": previous_day.get("games") if has_saved else None})
    save(DATA / "schedule.json", {
        "schema_version": 1, "generated_at": now(), "from_date": today.isoformat(),
        "through_date": days[-1]["date"], "game_date_timezone": "America/New_York",
        "source": "https://www.espn.com/nba/schedule", "days": days})
    return failures


def run(args):
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "days").mkdir(exist_ok=True)
    today = dt.datetime.now(ZoneInfo("America/New_York")).date()
    end = dt.date.fromisoformat(args.to_date) if args.to_date else today - dt.timedelta(days=1)
    start = dt.date.fromisoformat(args.from_date) if args.from_date else end - dt.timedelta(days=args.days - 1)
    if end < start:
        raise ValueError("--to must not precede --from")
    problems, score_success = [], 0
    # Schedule is always relative to today, even during an archive backfill.
    schedule_problems = refresh_schedule(today)
    problems.extend(schedule_problems)
    current = start
    while current <= end:
        day = current.isoformat()
        try:
            problems.extend(refresh_day(day, force=current >= end - dt.timedelta(days=1)))
            score_success += 1
            LOG.info("Scores: %s", day)
        except Exception as exc:
            problems.append(f"Scores {day}: {exc}")
        current += dt.timedelta(days=1)
    videos, video_success = [], False
    try:
        videos = read_feed()
        video_success = True
    except Exception as exc:
        problems.append(f"YouTube RSS: {exc}")
    if not args.skip_discovery:
        try:
            discovered = discover_videos(args.video_limit)
            # RSS has complete descriptions; prefer it over search snippets.
            ids = {v["id"] for v in videos}
            videos.extend(v for v in discovered if v["id"] not in ids)
            video_success = video_success or bool(discovered)
        except Exception as exc:
            problems.append(f"YouTube channel search: {exc}")
    for v in videos:
        if not v["date"] or not v["kind"]:
            continue
        # Don't create sparse older archive entries outside the requested backfill.
        path = DATA / "days" / f"{v['date']}.json"
        if not path.exists() and not (start.isoformat() <= v["date"] <= end.isoformat()):
            continue
        day = load(path, {"date": v["date"], "games": [], "videos": {}})
        previous = day["videos"].get(v["kind"], {})
        if previous.get("id") == v["id"]:
            v["chapters"] = max((v["chapters"], previous.get("chapters", [])), key=len)
        if v["kind"] == "recap" and not previous.get("metadata_enriched"):
            try:
                v = enrich_recap(v)
                v["metadata_enriched"] = v.get("metadata_enriched", False) or bool(v.get("duration_seconds"))
            except Exception as exc:
                LOG.warning("Recap metadata %s: %s", v["id"], exc)
        else:
            for key in ("metadata_enriched", "duration_seconds"):
                if key in previous:
                    v[key] = previous[key]
        day["videos"][v["kind"]] = v
        day["videos_checked_at"] = now()
        save(path, day)
    manifest = []
    for path in sorted((DATA / "days").glob("*.json"), reverse=True):
        day = load(path)
        date = dt.date.fromisoformat(day["date"])
        season_start = date.year if date.month >= 7 else date.year - 1
        manifest.append({"date": day["date"], "games": len(day.get("games", [])),
                         "scheduled_games": day.get("scheduled_games"),
                         "pending_games": day.get("pending_games", 0),
                         "season": f"{season_start}-{str(season_start + 1)[2:]}",
                         "top_plays": bool(day.get("videos", {}).get("top_plays")),
                         "recap": bool(day.get("videos", {}).get("recap"))})
    previous_index = load(DATA / "index.json", {})
    status = {"updated_at": now(), "days": manifest,
              "sources": {"videos": FEED, "scores": f"{API}/scoreboard"},
              "health": {"scores": "ok" if score_success else "error",
                         "videos": "ok" if video_success else "error",
                         "schedule": "error" if schedule_problems else "ok",
                         "warnings": problems},
              "last_successful_scores_at": now() if score_success else previous_index.get("last_successful_scores_at"),
              "last_successful_videos_at": now() if video_success else previous_index.get("last_successful_videos_at")}
    save(DATA / "index.json", status)
    for problem in problems:
        LOG.warning(problem)
    LOG.info("Archived %d dates; %d warnings", len(manifest), len(problems))
    # A partial source outage retains useful data but fails the Action visibly.
    return 1 if problems or not score_success or not video_success else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--from", dest="from_date")
    parser.add_argument("--to", dest="to_date")
    parser.add_argument("--video-limit", type=int, default=20)
    parser.add_argument("--skip-discovery", action="store_true")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    sys.exit(run(parser.parse_args()))
