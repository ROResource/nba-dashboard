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
- Roadmap captures standings/team stats and inline player season stats as planned, not implemented.
