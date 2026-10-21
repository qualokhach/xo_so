# AppNho Xổ số — Deep Audit V12

## Defects addressed
1. **Mixed-date traditional tables:** collector now refuses tables containing more than one distinct date rather than taking the first date found and assigning it to all stations.
2. **Station/date mismatch:** browser filters out known station records assigned to a weekday inconsistent with the normal draw schedule.
3. **Historical date selection:** browser attempts monthly partition loading for the selected date and reads the 25-month window at startup; it does not replace an unavailable date with a different date.
4. **Max 3D family display:** collector attempts to retain prize-category labels for Max 3D, Max 3D+, and Max 3D Pro when source markup exposes them.
5. **Regression coverage:** tests cover ambiguous dates, separate Max 3D identities, draw dates, number formats, and Lotto sessions.

## Local verification
- Python syntax compilation: PASS
- Pytest: 16 passed
- Inline JavaScript syntax (`node --check`): PASS
- ZIP integrity: to be checked after packaging

## Not claimed as verified
- Live source reachability or complete historical backfill.
- Correctness of every record already stored in the existing GitHub `data/` partitions.
- Browser rendering on the deployed GitHub Pages URL.
- Full 2-year history for every Vietlott product.

The repository is static. Selecting a date can only display historical results if that date's data exists in the relevant monthly JSON partition. A GitHub Actions backfill and live-site audit are required to verify end-to-end coverage. No missing results are invented.

## UI Landing Page Revision (2026-10-21)

The `index.html` content area was redesigned as a richer Vietnamese landing page while preserving the existing `<header>` markup and its branding/content. No footer markup was changed. Added: hero introduction and calls to action, quick category navigation, feature cards, section headings, responsive layouts, and improved spacing, color, tables, buttons, and empty states. The existing result-rendering logic, data paths, date picker IDs, tabs, and reload button were retained. Quick category links activate the corresponding existing tab and scroll to the result section.

Validation after UI changes:
- `python -m pytest -q`: 16 passed
- `python -m py_compile scripts/fetch_results.py`: passed
- `node --check` on the inline JavaScript extracted from `index.html`: passed

Scope note: these checks validate syntax, current automated tests, and static wiring. They do not constitute a live browser visual regression test against GitHub Pages or prove remote source availability/data completeness.
