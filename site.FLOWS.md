# Main flows and mobile scroll regression

- Open latest edition: both official video cards, recap chapters and completed games load.
- Browse dates: recent buttons, archive calendar and date query select the right edition; no-game days remain usable.
- Box scores: expand/collapse any game; both team player tables and quarter scores are visible.
- Mobile scrolling: a vertical touch gesture that starts over player rows scrolls the page, without moving horizontally. Horizontal touch gestures reveal more stats without moving the whole document sideways. Vertical scrolling must still work after a horizontal swipe.
- Score controls: filter to one team and restore all teams; hide scores and restore them.
- Videos: Top Plays and Recap create the right YouTube iframe; chapters and game buttons use the correct start seconds; outbound YouTube link remains available.
- Check desktop 1440px and mobile 375px, console errors, and document overflow.
- Deploy: verify updated CSS, scrolling and another main flow on GitHub Pages and the existing preview.

The bounded change is axis-specific overscroll behavior on `.table-scroll`. Preserve layout, content, data and update schedule.
