# NBA Daily upgrade roadmap

The goal is a streamlined daily catch-up: static prebuilt data, immediate local interactions and no browser calls to sports APIs. Preserve existing archive files and the current visual design.

## Delivered in the initial upgrade

- Easier box-score closing: a bottom close button, a contextual floating close control while reading an expanded game, and Escape support with focus returned to the game's summary.
- A compact, initially collapsed schedule showing today plus the next seven NBA game dates. This is eight dates in total, deliberately preserving today's fixtures as well as a full seven-day lookahead.
- Dublin/Eastern time selection with explicit calendar dates for games crossing midnight. NBA schedule grouping remains in America/New_York.
- One small `site/data/schedule.json`, loaded only on first opening and cached in memory. Date and timezone changes make no further requests.
- Schedule generation in the existing updater, per-day last-good fallback, explicit unavailable/stale states, validation and regression tests.

## Delivered: standings and team season stats

- Views: overall league, Eastern/Western conference and division.
- Start with verified provider fields: W, L, win percentage, games behind, streak, last ten, points for/against and differential.
- Treat league ordering as a comparison view, not official playoff seeding. Respect provider conference/division rankings and document tiebreak handling.
- Add offensive/defensive/net rating only if verified season-level data is available; do not label points differential as net rating.
- Prebuild one `standings.json` with explicit season, season type, source, timestamp and health.
- Lazy-load once when opened. Use compact view switches and local sorting without a new page or framework.
- Acceptance: rankings agree with the source, regular season and playoffs are not mixed, missing metrics show unavailable, mobile columns stay readable, and source failure preserves last-good data.

### Implementation

- Collapsed, lazy-loaded standings panel with League, Conference and Division views, local group selection, team filtering and statistics sorting.
- Current regular season is identified by the provider, independent of the selected archived game date.
- Conference ranks come from ESPN; division order preserves those ranks within provider-sourced division membership. League comparison sorts by percentage, wins and name and is explicitly not playoff seeding.
- Conference GB comes from the source. Division GB is calculated from that division's leader. GB is deliberately omitted from the league comparison.
- W-L, PCT, last ten, streak, points for/against per game and average point differential are displayed. Advanced efficiency/net ratings are not inferred.
- Exactly one small `standings.json` is fetched on first opening; all view/sort/search interactions reuse it. No logos or new image requests are needed.
- The existing Hide scores control also hides standings. Opening standings while scores are hidden makes no request.
- Two source requests per daily update produce one validated 30-team snapshot; incomplete, duplicate, wrong-season and inconsistent data preserve the entire last-good snapshot with an explicit stale label.

## Delivered: inline player season statistics

- Make a player name a keyboard-operable disclosure control; insert a slim detail row directly below that player.
- Start with GP, MPG, PPG, RPG, APG, SPG, BPG, turnovers and FG/3P/FT percentages.
- Show season and regular-season/playoff context explicitly. Use stable player IDs, handle traded players and DNPs, and distinguish current season stats from an archived game.
- Prebuild small season-keyed player files, for example `players/2026-27/regular/{playerId}.json`.
- Fetch only on first expansion, deduplicate concurrent requests, cache in memory and allow instant close/reopen.
- Refresh active players incrementally with bounded concurrency. Add a full refresh only if necessary without altering existing dispatch inputs or requiring a second scheduler.
- Acceptance: source-checked averages, correct percentage formatting, empty/error/retry handling, accessible expanded state, no table misalignment and smooth mobile panning.

### Implementation

- Player names are native disclosure buttons. Clicking inserts a compact row immediately beneath that player, without navigation or a new tab.
- Includes GP, MPG, PPG, RPG, APG, SPG, BPG, turnovers and FG/3P/FT percentages. Each row labels the season and regular-season/playoff context.
- Separate season/competition files preserve historical context. Scoreboard metadata identifies postseason games; older archive files without that metadata use explicitly labelled regular-season averages. Preseason games also reference regular-season averages, not preseason figures.
- Averages are season snapshots, not reconstructed statistics as of the archived game date. Traded players use the provider's combined all-team row.
- Tiny static player files load only on demand. Pending requests and completed responses are shared across games and archive dates for the same player/season/type.
- The updater uses four concurrent requests at most. First fill covers archived players; later runs refresh new appearances, retry failed data and perform weekly current-season correction checks.
- New player requests stop starting after a three-minute batch budget; in-flight requests retain the existing bounded HTTP timeouts. Deferred players keep last-good figures or an explicit unavailable placeholder, rather than holding up the archive indefinitely.
- GP checks reject provider rows that have not caught up with completed archived appearances. Last-good figures retain their observation time and get an explicit stale label.
- Players with no published stats receive an empty-state message, not fabricated zeros. Missing files/network failures get a local retry, without affecting the box score.
- Keyboard support includes Enter/Space, explicit expanded state, close/focus restoration and Escape to close the player row before the parent box score.
- The inline panel stays within the visible table viewport while panning and resizes without new requests. Existing box-score closing and score-hiding behavior is retained.

## Release and performance guardrails

- Keep the workflow name `Update NBA archive and deploy`, its filename `.github/workflows/daily.yml`, dispatch inputs and triggers unchanged. The Pi cron remains the scheduler; do not introduce or restore a GitHub schedule.
- No new runtime framework, database, API credentials, polling or third-party browser statistics requests.
- Keep the daily archive authoritative and backward-compatible. Supplementary data failures must not blank existing content.
- Aim for each supplementary JSON file to stay below 100 KB uncompressed; measure actual payloads and request counts before each release.
- Test Python generation, cross-file validation, archive navigation, video/chapter behavior, spoiler controls, team filters, empty/error/stale states, and mobile table scrolling.
- Verify both the GitHub Pages deployment and the existing preview. The preview is a snapshot; only GitHub Pages is updated by the daily Action.

## Intentionally outside this roadmap

Live scoring, betting features, complex advanced-stat dashboards and new notifications are not part of the requested catch-up experience.

All four requested feature upgrades are now implemented. Further feature work should follow real-use feedback; routine data-provider and workflow dependency maintenance must retain the existing dispatch contract.
