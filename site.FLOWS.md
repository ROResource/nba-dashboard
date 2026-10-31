# Main flows and mobile scroll regression

- Open latest edition: both official video cards, recap chapters and completed games load.
- Browse dates: recent buttons, archive calendar and date query select the right edition; no-game days remain usable.
- Box scores: expand/collapse any game; both team player tables and quarter scores are visible.
- Mobile scrolling: a vertical touch gesture that starts over player rows scrolls the page, without moving horizontally. Horizontal touch gestures reveal more stats without moving the whole document sideways. Vertical scrolling must still work after a horizontal swipe.
- Score controls: filter to one team and restore all teams; hide scores and restore them.
- Videos: Top Plays and Recap create the right YouTube iframe; chapters and game buttons use the correct start seconds; outbound YouTube link remains available.
- Check desktop 1440px and mobile 375px, console errors, and document overflow.
- Deploy: verify updated CSS, scrolling and another main flow on GitHub Pages and the existing preview.

## Initial upgrade acceptance checks

- Schedule is collapsed initially and makes no request until opened. First opening fetches one static JSON file; reopening and switching dates reuse it.
- Today plus the following seven Eastern game dates are shown, including no-game dates. Selecting a date updates only the schedule.
- Dublin times are the default; switch to Eastern and back. The displayed calendar date makes after-midnight games unambiguous.
- Schedule is explicitly a saved, non-live snapshot. Stale, partially unavailable, empty and failed-request states remain usable; retry recovers.
- Expanded games have a bottom close button. Once scrolled past the summary, a floating close button targets the visible expanded game.
- Closing returns focus and view to that game's summary. Escape closes when focus is inside the box score. Native summary toggling still works.
- Recheck score hiding, filters, archive navigation, videos, mobile two-axis table scrolling, desktop/mobile/short-window layout and console errors.
- Preserve `.github/workflows/daily.yml` byte-for-byte, including workflow name, dispatch inputs, jobs and triggers. Do not add a GitHub schedule.
- Roadmap distinguishes delivered standings/team stats from planned inline player season stats.

## Standings upgrade acceptance checks

- Initially collapsed; no standings request before first opening. One small static file, reused across view/group/sort/search changes and reopening.
- Conference view defaults to East; switch West. Division view exposes six provider-sourced groups. League comparison includes 30 unique teams.
- Use provider conference ranks; division order follows those ranks within each division. League sorts by win percentage, wins and team name, not official seeding.
- Conference GB uses provider data; division GB is computed relative to that division's leader. League omits GB.
- W-L, PCT, L10, streak, PF/G, PA/G and per-game differential match the generated snapshot. Missing optional metrics show unavailable, never zero.
- Sorting and search are local, group-specific and keep the original group rank visible. Switching archive dates does not change current-season standings.
- Spoiler toggle hides standings and makes no request if opened while scores are hidden. Restoring scores loads or reuses data without leaking records.
- Failed request/retry, unavailable snapshot, stale source and older saved timestamps are labelled. Supplementary failure must not stop archive updates.
- Desktop/mobile screenshots, sticky team names, horizontal/vertical touch scrolling, keyboard controls, overflow and console checks.
- Recheck all existing schedule/archive/video/filter/spoiler/box-score close flows and keep workflow byte-for-byte unchanged.

## Inline player season stats acceptance checks

- Player name is a native button with expanded state and a unique controlled row, including DNP players. No player request before a click.
- First click inserts a compact inline row directly below the player, within that team's table. Close/reopen is immediate and uses the session cache.
- Duplicate views of the same player/season/type share a pending request and cached response. Archived seasons and playoffs have distinct cache/file keys.
- Show explicit season, regular season/playoff context, GP, MPG, PPG, RPG, APG, SPG, BPG, turnovers and shooting percentages. Use combined all-team averages for trades, never add rounded averages.
- Season averages are full-season-to-date snapshots, not statistics as of the archived game date. Preseason games reference clearly labelled regular-season averages.
- Empty/DNP, stale, unavailable and network error/retry states stay inside the row. Changing dates or hiding scores during a pending request must not modify another table.
- Escape first closes the focused player disclosure and returns focus to its name; a second Escape can close the box score. Existing bottom/floating close controls still work.
- Mobile inline content stays within the visible table viewport while panning; vertical page scrolling, horizontal table scrolling, resize and sticky sizing remain usable.
- Regression-check schedule, standings, filters, score hiding, archive/calendar, video/chapter controls, box closing and console errors. Workflow remains unchanged.
