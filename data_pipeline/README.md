# Daily Job Data Pipeline

This folder contains the planned ingestion workflow for keeping the job catalog current.

## Safety principles

- The existing Streamlit app and trained model are not changed by this pipeline.
- Never treat repeated template rows as distinct job postings.
- Keep source attribution, source URL, external job ID, first-seen and last-seen timestamps.
- Normalize job titles and skill aliases, but send unknown skills to a review queue.
- Calculate skill demand from distinct active postings.
- Preserve the app export columns: `job_id`, `category`, `job_title`, `job_description`, `job_skill_set`.
- Do not retrain the compatibility model from unlabelled incoming postings.
- Do not publish a refreshed catalog until validation checks pass.

## Planned components

1. Source adapter — fetches postings from a verified provider/API.
2. Normalizer — standardizes titles, locations, descriptions and skill aliases.
3. Deduplicator — prefers provider job ID; falls back to canonical URL and content fingerprint.
4. Skill review queue — records candidate skills not yet in the approved taxonomy.
5. Catalog builder — exports the app-compatible CSV and demand statistics.
6. Validation — checks schema, duplicates, empty descriptions, row counts and source freshness.
7. Scheduler — GitHub Actions daily workflow after a source and credentials are configured.

## Current status

This is a design scaffold only. No external job source has been connected yet. Configure a provider only after its API, India coverage, description availability, rate limits and licence/terms have been verified.
