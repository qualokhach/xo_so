# AppNho Xổ số — History Integration Bundle

This bundle adds a separate immutable historical dataset to the AppNho lottery site.

- `data/history/YYYY-MM.json`: historical records by month
- `data/history/index.json`: history manifest
- `data/archive/`: live data area; keep your existing contents when merging
- `index.html`: date picker loads a selected month's live and history partitions
- `scripts/fetch_results.py`: routine collector remains scoped to `data/archive/`, not history
- `tests/test_history_import.py`: tests for history partitions, product separation, Lotto retention, and 3-digit strings

**Important:** do not replace your live `data/archive/` or `data/index.json` with files from this bundle. Copy/merge the new history folder and updated app/workflow into the existing repository.
