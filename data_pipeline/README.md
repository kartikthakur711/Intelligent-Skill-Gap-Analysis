# Daily Job Data Pipeline

This folder contains the catalog quality utilities and a bounded Headcount Labs importer.

## Safety principles

- The model and production catalog stay unchanged; the app may display aggregate daily counts as a supplementary signal.
- Never treat repeated template rows as distinct job postings.
- Do not collect or persist source URLs or posting-level records in this importer.
- Match only skills already in the catalog taxonomy; new skills are not added automatically.
- Calculate skill demand from distinct active postings.
- Keep source descriptions and job records in memory only; do not publish them from this public repository.
- Publish aggregate category/skill counts and normalized job-title counts with shared window metadata. job_catalog.csv remains unchanged.
- Title aggregates contain only distinct provider title strings and record counts; never publish descriptions, URLs, or posting-level records.
- Do not retrain the compatibility model from unlabelled incoming postings.
- Do not publish a refreshed catalog until validation checks pass.

## Pipeline behavior

1. `headcount_importer.py` requests current, non-stale India jobs updated in the preceding 48 hours.
2. It pages with stable filters and uses a 250 unique-job cap; incomplete/over-cap runs fail.
3. Existing catalog skills provide the approved taxonomy; descriptions are processed in memory.
4. The outputs contain category/skill counts and distinct title counts plus the update window and generation time; they are uploaded as a 14-day Actions artifact.
5. The workflow commits aggregates on main. The app displays recent titles separately from analysis-ready catalog roles; model scores and job_catalog.csv do not change.
6. Run offline tests with `python -m unittest discover -s data_pipeline -p 'test_*.py'`.

## Current status

Headcount Labs documentation was checked on 2026-10-24. It documents bearer-key authentication, GET /v1/jobs, country IN, posted_since, currentness and stale filters, selected fields, and opaque next_cursor pagination. Terms permit analytics subject to third-party rights; the open-data licence does not grant rights to job-board text or personal data. The live API key and importer were verified by a successful Actions run on 2026-10-24. The daily schedule is 02:17 UTC (07:47 India time). The 250-record cap bounds each run; API allowance remains shared at the account level.

The importer publishes a sibling `.metadata.json` file with API record count, usable-description count, taxonomy match count, distinct title count, time window, snapshot watermark and cap. It contains no posting text. The app requires the title aggregate and valid metadata to show recent titles and distinguish empty, stale, malformed, or missing data.

The 48-hour demand window uses the source publication date (`posted_since`), matching the app’s recent-listing label. The importer retains the provider snapshot watermark for run diagnosis; Headcount does not guarantee when source changes appear in its catalog.
