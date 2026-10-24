# Daily Job Data Pipeline

This folder contains two distinct utilities: a source-agnostic catalog deduplication/quality-report tool and a bounded Headcount Labs importer for aggregate skill-demand reporting. Neither utility updates the app catalog or model automatically.

## Headcount importer

`headcount_importer.py` sends a request to `GET https://api.headcountlabs.com/v1/jobs` using bearer authentication from `HEADCOUNT_API_KEY`. The workflow defaults to India (`country=IN`), current and non-stale jobs, and `updated_since` equal to the preceding 48 hours. It requests `job_id,title,description`, sorts by update time, and follows opaque cursor pagination. It checks that the snapshot watermark remains stable during pagination, deduplicates by job ID, and fails if the walk would exceed its 250 unique-job safety cap instead of silently truncating.

The existing catalog supplies the known skill taxonomy. The importer matches known skill strings against title and description in memory. It writes only `category`, `skill`, and `distinct_job_count` to CSV. Posting descriptions, titles, and identifiers are not included in the output. The workflow uploads the CSV as a GitHub Actions artifact with 14-day retention; it does not commit fetched data or change `job_catalog.csv` or `resume_job_ml_model.pkl`.

Run offline tests:

```powershell
python -B -m unittest discover -s data_pipeline -p 'test_*.py' -v
```

To run a live import, set `HEADCOUNT_API_KEY` in the environment and run:

```powershell
python data_pipeline/headcount_importer.py --catalog job_catalog.csv --output build/headcount_skill_demand.csv --max-records 250
```

Do not expose the key in shell history or logs. The importer accepts `--updated-since` (RFC 3339 timestamp) and `--max-records` (1–1,000). The API key, allowance, and a live response must be checked in the intended GitHub Actions environment before relying on scheduled output.

## Workflow configuration and integration limits

The workflow is `.github/workflows/daily-job-data.yml`. It runs on pushes to `feature/daily-job-data-pipeline`, manual dispatch, and a daily schedule at 02:17 UTC. It explicitly checks out the feature branch. GitHub scheduled workflows run only when the workflow file is on the repository's default branch; the schedule therefore depends on this workflow being present there and the feature branch containing the intended code.

The aggregate is currently separate from app ranking. `skill_prioritization.py` counts occurrences in `job_catalog.csv` rows, including repeated/template rows; it does not read the Headcount artifact. The Headcount output is not a model label and must not trigger retraining. The production catalog should only be refreshed through a separately reviewed process with data quality, rights, and privacy checks.

## Catalog quality utility

`build_catalog.py` accepts an input catalog, emits a deduplicated five-column catalog, and writes a JSON quality report. Its dedup key prefers `source_job_id`, then `job_url`/`canonical_url`, then a normalized title/description/skills fingerprint. It does not modify the input file. Its fallback fingerprint is a heuristic and cannot guarantee two rows represent the same or different real-world vacancy.

## Data and rights notes

Headcount API documentation was reviewed on 2026-10-24. Check current service terms, API access, quota, and third-party rights before production use. The upstream open-dataset licence does not by itself grant rights to employer/job-board text or personal data. The importer uses descriptions only in memory and exports aggregates, but this handling does not replace a legal/privacy review for the intended deployment.
