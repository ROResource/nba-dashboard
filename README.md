# NBA Daily

A small GitHub Pages dashboard for a next-morning NBA catch-up:

- Official NBA Top 10 or Top 5 Plays, embedded on demand.
- Official NBA Nightly Recap, with timestamp buttons and game-specific recap links.
- Final scores, quarter scores and expandable player box scores for both teams.
- Recent-date buttons, full archive date picker, team filtering and a hide-scores switch.
- Today plus the next seven game dates in a compact schedule, with Dublin/Eastern times.
- Bottom and contextual floating box-score close buttons, plus Escape support.
- League, conference and division standings with team records, last ten, streak and points per game.
- Inline player season averages beneath each clicked name, including DNP player disclosures and keyboard controls.
- Daily GitHub Actions updates and a permanent date-based archive.

## Website

[Open NBA Daily](https://roresource.github.io/nba-dashboard/)

## How updates work

The Raspberry Pi's external cron dispatches the existing **Update NBA archive and deploy** workflow. The workflow file is `.github/workflows/daily.yml`; its name, dispatch inputs and triggers remain unchanged by this upgrade. There is currently no native GitHub `schedule` trigger. The site shows its last update time in Europe/Dublin time.

Data processing and deployment run entirely on GitHub. No Perplexity fallback automation is configured. If an external trigger is missed, the next trigger or a manual dispatch can catch up. Pushes affecting the website, scripts, tests or workflow also trigger an update.

The default update revisits the last seven NBA game dates. It fetches only completed games, rechecks the latest two days for corrected box scores, retries missing box scores and never deletes older archive dates. Dates use **America/New_York**, not the video's UTC publication date. A video titled “October 24” belongs to October 24 even if uploaded on October 25.

Data lives in `site/data/days/YYYY-MM-DD.json`. `site/data/index.json` is the lightweight archive manifest. Browsers request only the selected day, not the entire season. Archives survive in the repository and Git history. New seasons do not erase previous seasons.

The updater also builds `site/data/schedule.json` for today through today + seven days, using Eastern game dates regardless of archive backfill inputs. The schedule panel is initially collapsed and fetches this small snapshot only when first opened. Date/timezone switches and reopening reuse it in memory. Tip-off timestamps are stored with their timezone and displayed with explicit local dates, so games after midnight and daylight-saving changes are unambiguous. No live scores or browser sports-API requests are added.

Each schedule date has its own observation time and health status. A failed refresh retains that date's previous fixtures; a date with no saved data is explicitly unavailable rather than falsely reporting no games. Stale snapshots are labelled in the UI. The schedule is not a live service, and fixtures may change between updates.

`site/data/standings.json` is a separate current regular-season snapshot, requested only when its collapsed panel is opened. League, conference and division views, group selection, team search and statistic sorting run locally without more requests. Conference order uses provider ranks; division order preserves those ranks within provider-sourced division membership. League order is a win-percentage comparison, not official playoff seeding. Division games-behind is calculated within the selected division; conference GB is provider-sourced, and league GB is omitted.

Team season columns include W-L, win percentage, last ten, streak, points for/against per game and average point differential. Differential is not net rating. Missing optional figures are unavailable rather than zero. Standings reflect the current provider season, not the selected archived date, and respect the existing Hide scores control. Failed or incomplete source responses preserve the last-good snapshot and its observation time. No new scheduler, workflow inputs, credentials or browser sports-API calls are introduced.

Player data lives in `site/data/players/{season}/regular/{playerId}.json` or the corresponding `playoffs` directory. Clicking a player's name opens a small inline row containing games played, minutes, points, rebounds, assists, steals, blocks, turnovers and shooting percentages. The browser loads only that player's static file and shares its pending request/result across all instances in the session. No player requests occur at initial load or merely when opening a game.

The displayed figures are labelled season snapshots, not stats reconstructed as of an archived game date. Provider scoreboard metadata selects playoff context; older files without phase metadata and preseason games use clearly labelled regular-season averages. Traded players use the provider's combined all-team season row. Shooting percentages retain the provider's 0–100 scale.

The updater bootstraps archived player contexts using at most four concurrent requests. Subsequent runs refresh new appearances, retry missing data after a one-hour cooldown, and recheck current-season snapshots weekly for corrections. It rejects season GP counts behind completed archived appearances and preserves last-good data on failure. A no-published-stats message is distinct from a failed request; neither produces fabricated zero averages. The browser supports local network retry, instant close/reopen, accessible expanded state, focus restoration and Escape. On mobile the inline panel stays visible while the enclosing box score pans.

To protect the daily update during a provider outage, no new player requests start after a three-minute batch budget. Requests already in flight retain the existing bounded timeouts. Deferred contexts keep last-good figures or an explicit unavailable placeholder, and warning lists are capped to keep the archive manifest small.

The updater merges existing data, retries HTTP failures, preserves previous box scores on failure, validates the output, commits changed JSON, and deploys the `site` directory with the official Pages Actions. A partial upstream outage still deploys the last available data but marks the workflow failed, rather than silently reporting success.

No API key, paid service, database, running backend or Perplexity session is needed after installation.

## Sources and limitations

- **Videos:** [official NBA YouTube channel](https://www.youtube.com/@NBA) and its [public RSS feed](https://www.youtube.com/feeds/videos.xml?channel_id=UCWJ2lWNubArHWmf3FIHbfcQ). The updater uses `yt-dlp` only for public metadata discovery on the official channel, never to download video or audio. Channel searches fill gaps when the recent-upload RSS feed rolls over.
- **Chapters:** timestamps in the official video's public description. If descriptions are unavailable, complete timestamps from RSS or channel results are retained. Missing chapters are not invented. Embedded YouTube playback and its own chapter controls remain available.
- **Scores:** [ESPN scoreboard](https://www.espn.com/nba/scoreboard) and public site JSON endpoints under `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/`. These are undocumented site endpoints, not a contracted developer API. Availability and schemas can change. The source URL is stored with each game, and full box-score links are provided.
- **Playback:** official YouTube iframe embeds only. Videos are not copied or rehosted. YouTube can restrict embedding, regional availability or playback. Every video has a Watch on YouTube fallback link.
- **Archive coverage:** scores can be backfilled separately from videos. Channel search is bounded and may not return every historical upload. A missing video is shown as unavailable for that date, never replaced with an unrelated day's video.
- **Spoilers:** hiding scores conceals final scores, game-time records and box-score details, but cannot prevent spoilers in YouTube thumbnails, playback or chapter titles.
- **Inactive repositories:** GitHub can disable scheduled workflows in public repositories after extended inactivity. Check the Actions page if updates stop; re-enable the workflow and run it manually.

This independent personal dashboard is not affiliated with or endorsed by the NBA, ESPN or YouTube. It uses external sources subject to their terms and availability.

## Manual update or season backfill

Open **Actions → Update NBA archive and deploy → Run workflow**.

Leave inputs blank for the rolling seven-day refresh. To backfill a season, supply a start date and optionally an end date. Use month-sized batches for large historical ranges to stay within the job timeout. Increase `video_limit` for more channel-search results; video discovery is not guaranteed exhaustive.

From a local checkout:

```bash
pip install -r requirements.txt
python scripts/update.py
python scripts/update.py --from 2026-10-20 --to 2026-10-24 --video-limit 50
python scripts/validate.py
python -m unittest discover -s tests -v
python -m http.server 8000 --directory site
```

## Repository settings

GitHub Pages must use **GitHub Actions** as its build source. The workflow needs `contents: write`, `pages: write` and `id-token: write`. It commits only public JSON data. No credentials appear in the static website.

All four requested upgrades are implemented. See [the upgrade roadmap](ROADMAP.md) for delivery details and guardrails. Live scoring remains outside the catch-up scope.
