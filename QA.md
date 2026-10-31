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

## Initial upgrades, 31 October 2026

- Added today plus seven further Eastern game dates. The fetched snapshot covers 31 October through 7 November, with seven fixtures on the first date.
- Schedule payload measured 17,516 bytes uncompressed. Browser requests: zero schedule requests at initial page load, one on opening, no further requests for date/timezone switches or reopening.
- Verified Dublin/Eastern time changes, explicit after-midnight dates, all eight date buttons and independence from the selected archive edition.
- Verified failed-request/retry recovery and simulated empty, stale and partially unavailable schedule dates. Existing archived games remained usable.
- Verified bottom and floating close controls, native summary toggling, Escape, and focus restoration to the correct game's summary.
- Rechecked archive buttons, date picker, team filter, hide/show scores, video iframe selection, recap chapters/game links and outbound YouTube fallback.
- Checked desktop 1440×900, short desktop 1440×600, mobile 375×812 and resizing desktop → mobile → desktop. No document-level horizontal overflow or first-party JavaScript errors.
- Mobile touch panning over player tables moved the page 227px vertically and the table 216px horizontally; vertical panning still worked after horizontal panning.
- Reviewed screenshots of the collapsed initial view, expanded schedule and mobile expanded box score with the floating close control.
- The workflow file is unchanged byte-for-byte. It has no native GitHub schedule; the external Pi cron dispatch remains intact.
- Standings/team stats and inline player season stats are documented in `ROADMAP.md`; they are not yet implemented.
- All 16 Python unit tests, JavaScript syntax checks and generated-data validation passed.
- [Release workflow 41191529203](https://github.com/ROResource/nba-dashboard/actions/runs/41191529203) completed successfully, including data refresh and GitHub Pages deployment.
- Fresh browser contexts verified the updated GitHub Pages site and the existing NBA Daily preview: schedule loading, date/timezone switching, floating/bottom closing, and existing score controls passed with no first-party JavaScript errors.

## Standings upgrade, 31 October 2026

- All 24 Python unit tests passed, including complete/partial/wrong-season source data, duplicate memberships/ranks, invalid metrics, zero values, last-good fallback and failure isolation from the archive.
- Generated-data validation passed for 13 archived dates, 81 completed games, eight schedule dates and a complete current regular-season standings snapshot. JavaScript syntax and whitespace checks passed.
- Standings payload measured 11,147 bytes uncompressed. Browser requests: zero before opening; one on first opening; no further requests for view/group/sort/search changes, score toggles or reopening.
- Verified both conference groups, all six five-team divisions and the 30-team league comparison. All 30 displayed records, percentages, last ten, streak and per-game figures were checked against the generated source snapshot.
- Checked provider conference ordering, division leader-relative GB, omitted league GB, local PF/PA/differential sorting, preserved rank labels, team search and no-match recovery.
- Opening while scores are hidden makes no request. Hide scores conceals already loaded standings; restoring scores reuses the snapshot.
- Simulated failed request/retry, stale source with original observation time, missing optional metrics and a wholly unavailable snapshot. Missing metrics sort last and display unavailable, never zero.
- Switching the archive date leaves current-season standings unchanged.
- Inspected desktop 1440×900 and mobile 375×812 screenshots, plus short desktop 1440×600 and resizing. No document-level horizontal overflow or first-party JavaScript errors.
- Mobile standings touch tests moved the page 194px vertically and the table 220px horizontally. Sticky team names remained at x=33px; vertical scrolling still worked after horizontal panning.
- Rechecked schedule dates/timezones, archive/calendar navigation, team filter, score hiding, bottom/floating/Escape box-score closing and focus restoration, video selection and recap chapters/game links. Mobile box-score scrolling still works.
- Workflow file `.github/workflows/daily.yml` remains byte-for-byte unchanged, including name, triggers and dispatch inputs.
- [Standings release workflow 41192150519](https://github.com/ROResource/nba-dashboard/actions/runs/41192150519) completed successfully and the new version was verified on GitHub Pages.
- Fresh-context hosted checks passed on both GitHub Pages and the existing preview: all three standings views, groups, search/sort, spoiler behavior, one-request loading, schedule, archive/calendar, team filter, box-score closing, video loading and 375px layout. No first-party JavaScript errors.

## Inline player statistics upgrade, 31 October 2026

- All 39 Python tests passed. New coverage includes per-game versus career rows, season/competition separation, traded-player combined rows, percentage scale, zero/missing/invalid values, DNP/preseason handling, incremental refresh, weekly correction, last-good fallback, GP lag detection, retry cooldown and request-budget deferral.
- Generated-data validation passed for the existing archive/schedule/standings and 457 player-season snapshots. At bootstrap, 430 contained figures, 25 had no published season stats and two had provider season rows not yet caught up with completed games. The latter are explicitly unavailable and retried automatically, not populated with career figures or invented zeros.
- Player JSON payloads averaged 461 bytes, with a largest file of 480 bytes; the complete 457-file bootstrap was 210,576 bytes uncompressed. None of these files is loaded at initial page load or merely when opening a game.
- First click makes one static player request; close/reopen uses the session cache. Verified pending-request sharing across close/reopen and archive navigation, and safe handling when the archive changes or scores are hidden before the response arrives.
- Verified that each row is directly beneath its player, spans the existing table columns and displays all 11 requested fields with 0–100 percentage formatting.
- Source spot-check: the rendered Moussa Diabate season row agrees with [ESPN's regular-season averages](https://www.espn.com/nba/player/stats/_/id/4433249), including 6 GP, 29.7 MPG, 9.3 PPG, 9.8 RPG, 1.8 APG and 62.2% FG.
- Tested real DNP-name activation, local request error/retry, missing percentage, no-published-stats and unavailable messages, plus stale data with its original observation timestamp.
- Synthetic season/phase fixtures confirmed separate `2025-26/playoffs` and `2026-27/regular` requests/cache keys for the same player. Production averages are season snapshots, not reconstructed as of an archived game date.
- Enter and Space open the disclosure. Close returns focus to the player; Escape closes the player row first, then the box score. All rendered ARIA control references point to existing rows.
- Reviewed desktop and 375×812 mobile screenshots. Metrics reflow without overlap; the panel stays within the visible table viewport while panning.
- Mobile touch tests moved the table 231px horizontally and the page 195px vertically over the inline panel. The panel's left edge remained at x=33px. Closing, 1440×600 short-window layout and desktop/mobile resizing passed without document-level horizontal overflow.
- Rechecked schedule dates/timezones, all standings views, search/sort, score hiding, team filtering, archive/calendar, bottom/floating/Escape box closing, video selection and recap chapters/game links. These flows made zero incidental player requests. No first-party JavaScript errors.
- Player refresh concurrency is capped at four. New requests stop starting after a three-minute batch budget, with bounded in-flight timeouts and explicit deferred states. Warning lists are capped to keep the archive manifest small.
- Workflow file `.github/workflows/daily.yml` remains byte-for-byte unchanged, including name, filename, inputs and triggers.
