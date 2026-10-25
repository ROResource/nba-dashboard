# NBA Daily

A small GitHub Pages dashboard for a next-morning NBA catch-up:

- Official NBA Top 10 or Top 5 Plays, embedded on demand.
- Official NBA Nightly Recap, with timestamp buttons and game-specific recap links.
- Final scores, quarter scores and expandable player box scores for both teams.
- Recent-date buttons, full archive date picker, team filtering and a hide-scores switch.
- Daily GitHub Actions updates and a permanent date-based archive.

## Website

[Open NBA Daily](https://roresource.github.io/nba-dashboard/)

## How updates work

The workflow runs at **06:17, 08:17, 10:17, 12:17 and 16:17 UTC** every day. Multiple passes catch late final games and delayed video uploads. Scheduled GitHub Actions runs can be delayed by GitHub; these are not guaranteed publication times. The site shows its last update time in Europe/Dublin time.

The default update revisits the last seven NBA game dates. It fetches only completed games, rechecks the latest two days for corrected box scores, retries missing box scores and never deletes older archive dates. Dates use **America/New_York**, not the video's UTC publication date. A video titled “October 24” belongs to October 24 even if uploaded on October 25.

Data lives in `site/data/days/YYYY-MM-DD.json`. `site/data/index.json` is the lightweight archive manifest. Browsers request only the selected day, not the entire season. Archives survive in the repository and Git history. New seasons do not erase previous seasons.

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

The initial version deliberately does not include live scores, standings or season-stat screens.
