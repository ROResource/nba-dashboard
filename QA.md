# Acceptance checks

- Latest archived edition shows official Top 10/5 and Nightly Recap for the same game date.
- Play buttons create the official embed; YouTube fallback opens the corresponding video.
- Recap chapter buttons and each matched game's recap button load the correct start second.
- Each final game has home/away score, quarter scores and both player tables.
- Archive date buttons, date picker and a date deep link select the requested day.
- All-teams filter changes visible games and resets cleanly.
- Hide/show scores is reversible and conceals records and box-score details.
- No-game date and a missing archive date show meaningful empty states.
- A failed archive fetch gives retry instructions, not a blank screen.
- Rapid date changes cannot show another date's content.
- Desktop, 375px mobile, expanded tables and short desktop window have no page overflow.
- No first-party browser console errors; third-party playback restrictions are disclosed separately.
- Python tests and cross-file data validation pass.
- Deployed Pages URL and private preview load the current version.
- Initial GitHub workflow completes and scheduled runs are registered.

## Verification, 25 October 2026

- Eight Python unit tests passed. Archive validation passed for seven dates and 36 completed games.
- Both initial GitHub update-and-deploy runs completed successfully.
- Public Pages site returned HTTP 200 and rendered eight games and nine recap chapters for 24 October.
- Desktop 1440px, short-window 1440×600 and mobile 375px views checked. No document-level horizontal overflow.
- Both player tables and quarter table rendered for an expanded game. Mobile table horizontal scrolling checked.
- Recent-date navigation, calendar input, direct date URL, team filtering, score hiding and restoring, and rapid successive date changes checked.
- Empty game day and missing archive date checked.
- An intentionally failed manifest request showed a retry button; restoring access and clicking retry recovered all eight games.
- Recap game button generated `start=157` for Heat at Hornets. Switching to Top Plays removed the previous player.
- YouTube fallback opened the correct video in a separate tab.
- No first-party JavaScript errors during browser tests. Sampled secondary-text and accent contrast ratios were at least 7.48:1.
- Official iframe creation and start positions were verified. End-to-end audiovisual playback is provider-controlled and was not independently certified in the headless test browser.
- GitHub Pages is the automatically updating site. The attached Perplexity preview is a snapshot, not a separately scheduled deployment.

## Mobile table-scroll correction

- Replaced both-axis scroll containment on stats tables with horizontal-only containment and normal vertical chaining.
- Explicitly allowed native two-axis panning and pinch zoom; no JavaScript gesture interception.
- Versioned the stylesheet URL to avoid reusing the old cached CSS.
- Chromium mobile touch-input test over player rows moved the page 202px vertically.
- Horizontal touch-input test moved the stats table 256px; a subsequent vertical swipe moved the page 203px.
- No horizontal document overflow or first-party JavaScript errors. Date browsing, score visibility, team filtering, recap links, video selection and desktop expansion were rechecked.
