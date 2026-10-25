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
