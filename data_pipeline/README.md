# Daily Job Data Pipeline

This folder contains the catalog quality utilities and a bounded Headcount Labs importer.

## Safety principles

- The existing Streamlit app and trained model are not changed by this pipeline.
- Never treat repeated template rows as distinct job postings.
- Keep source attribution and source URLs only where the applicable rights permit.
- Normalize job titles and skill aliases, but send unknown skills to a review queue.
- Calculate skill demand from distinct active postings.
- Keep source descriptions and job records in memory only; do not publish them from this public repository.
- Publish only aggregate category/skill counts. The production catalog remains unchanged.
- Do not retrain the compatibility model from unlabelled incoming postings.
- Do not publish a refreshed catalog until validation checks pass.

## Planned components

1. `headcount_importer.py` requests current, non-stale India jobs updated in the preceding 48 hours.
2. It pages with stable filters and uses a 250 unique-job cap; incomplete/over-cap runs fail.
3. Existing catalog skills provide the approved taxonomy; descriptions are processed in memory.
4. The output contains only `category`, `skill`, and `distinct_job_count`, uploaded as a 14-day Actions artifact.
5. The workflow uses `HEADCOUNT_API_KEY` and never echoes it. It does not commit fetched data or change the app catalog/model.
6. Run offline tests with `python -m unittest discover -s data_pipeline -p 'test_*.py'`.

## Current status

Headcount Labs documentation was checked on 2026-10-24. It documents bearer-key authentication, `GET /v1/jobs`, country `IN`, `updated_since`, `currentness`, `stale`, selected fields, and opaque `next_cursor` pagination. The importer uses the API only for aggregate skill-demand analysis and writes no source posting text. Headcount's service terms permit analytics subject to third-party rights; its open dataset licence does not cover employer/job-board text or personal data. API credentials, allowance and live response have not been validated by a workflow run. The daily schedule will start only after this workflow is available on the repository's default branch; this feature branch has not been merged.
