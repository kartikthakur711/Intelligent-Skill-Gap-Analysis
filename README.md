# Intelligent Skill Gap Analysis

## React application (new, optional frontend)

The existing Streamlit app remains available through `app.py`. The React application in `web/` is a separate frontend served by Vite locally or as static assets in production. It talks to the FastAPI service in `api.py`; both use the existing saved model, job catalog, learning resources, recent listing aggregates, and file-backed learning progress. The compatibility feature order and score clipping remain the same as the Streamlit app. The model is loaded as-is and is never retrained or overwritten by the API.

The UI exposes Overview, Resume analysis, Explore jobs, Skill gaps, Learning roadmap, and My progress. Role filters use categories actually present in `job_catalog.csv`; the data does not classify roles as technical or non-technical. Dashboard catalog mentions and recent India listing aggregates are labeled separately and are not presented as vacancy totals. Resume files are processed in memory by the API and are not written to disk. Progress keeps the existing hashed profile label and file-store behavior; this is local/single-instance convenience, not authentication or private multi-user storage.

### Local setup

In one terminal, install Python requirements and start the API:

```sh
python -m pip install -r requirements.txt -r requirements-api.txt
uvicorn api:app --reload --port 8000
```

In another terminal, install the web packages and start the React app:

Use Node.js 22 and pnpm 11 (enable pnpm with `corepack enable` if needed).

```sh
cd web
pnpm install
pnpm dev
```

Open the Vite URL shown in the terminal (normally `http://localhost:5173`). Vite proxies `/api` to `http://localhost:8000`. The first resume analysis loads `all-MiniLM-L6-v2`; allow the API runtime to download it or pre-cache the model. The uploaded resume must contain at least 50 extractable characters. Text-based PDFs work best.

### Build and tests

```sh
cd web
pnpm test
pnpm build
```

From the repository root, run the API contract tests with:

```sh
python -B -m unittest discover -s tests -p 'test_api_contract.py' -v
```

### Deployment

No deployment platform configuration exists in this repository today. Keep the current Streamlit deployment command (`python -m streamlit run app.py`) as the rollback path. For a staged React rollout, deploy `web/dist` to a static host and run `uvicorn api:app --host 0.0.0.0 --port 8000` as a separate Python service. Set `VITE_API_URL` at frontend build time to the API origin and set `SKILLSCOPE_CORS_ORIGINS` on the API to the exact static frontend origin(s), comma-separated. Keep the bundled `resume_job_ml_model.pkl`, `job_catalog.csv`, learning resources, and `data_pipeline` aggregates in the API image or mount them at the configured paths. The API loads the existing sklearn artifact and sentence model; provision a compatible Python/scikit-learn environment and cache or allow download of the sentence model before exposing the service.

Install `requirements-api.txt` alongside the existing Python requirements in the API image; the Streamlit-only install can continue using `requirements.txt` unchanged. Set `LEARNING_PROGRESS_FILE` to durable storage for a single API process. The current JSON store is not shared across replicas and has no authentication; production multi-user deployment requires authenticated profiles and a shared durable storage adapter before enabling progress for multiple users. Do not expose a shared API as a private multi-user service without that work. The daily job-data GitHub Actions workflow is unchanged and continues to publish aggregate CSV snapshots. This change does not deploy, modify the existing hosted Streamlit service, change its entry point, or merge to `main`.

### API contracts

- `GET /api/health` reports service and bundled artifact availability.
- `GET /api/dashboard` returns catalog roles/categories, catalog skill mentions, validated optional recent listing snapshots, and aggregate saved progress.
- `POST /api/analyze` accepts multipart `resume`, `job_title`, and an optional `profile` (defaults to `default`); it returns the model score, descriptive signals, matched/missing skills, catalog priority, resource recommendations, prerequisite-ordered roadmap, saved completion for that profile, and the original prototype-score caveat.
- `POST /api/progress` accepts `profile`, `job_title`, `roadmap`, and `completed_skills`, then returns the persisted completion and aggregate summary.

## Project Overview

This project is an Intelligent Skill Gap Analysis and Personalized Learning Recommendation System.

The system compares a user's resume with a target job and identifies matched and missing skills. It then prioritizes skill gaps and creates a personalized learning roadmap with learning resources.

## Project Flow

Resume
→ Resume Skill Extraction
→ Target Job Title
→ Job Description Dataset
→ Required Skill Extraction
→ ML Compatibility Prediction
→ Matched / Missing Skills
→ Skill Prioritization
→ Personalized Learning Roadmap
→ Learning Resources

## Main Features

- Resume upload and skill extraction
- Job-title-based job retrieval
- Resume-job skill matching
- ML-based compatibility score
- Missing-skill identification and prioritization
- Personalized learning roadmap
- Learning-resource links
- Saved learning progress for roadmap steps
- Streamlit web application

## Run Locally

Use Python 3.11 (Python 3.10 or newer is required). From the repository folder, create and activate a virtual environment, then install the dependencies.

**Windows PowerShell**

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

**macOS or Linux**

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Start the application from the repository folder:

```sh
python -m streamlit run app.py
```

The app uses the included model, job catalog and learning resources. On first analysis, Sentence Transformers downloads the `all-MiniLM-L6-v2` model, so the first run needs internet access. Upload a PDF, DOCX or TXT resume and enter a target job title. The app itself does not need the Headcount API key; the daily GitHub Actions pipeline uses its configured repository secret.

To run the pipeline offline tests locally:

```sh
python -B -m unittest discover -s data_pipeline -p 'test_*.py' -v
```

## Demonstration Walkthrough

1. Start the app and open **Analyze resume** from the sidebar.
2. Upload a text-based PDF, DOCX, or TXT resume and enter a role represented in the catalog, such as **Machine Learning Engineer**, **Data Scientist**, or **Software Engineer**.
3. Review the selected role, compatibility estimate, matched skills, and missing skills. The estimate is a prototype score trained on constructed labels; it is not a hiring probability.
4. Follow the ranked learning plan, open the linked resources, mark completed steps, and save progress under a nickname. Use a non-sensitive label because profile separation is local convenience, not authentication.
5. Return to **Dashboard** to show catalog skill mentions, the separate recent-listing snapshot when available, and saved progress totals.

The first resume analysis may download the `all-MiniLM-L6-v2` sentence model. Allow internet access for that first run, or pre-cache the model in the runtime image. The bundled model artifact and catalog are used as-is; the demonstration does not retrain them.

## Deployment Preparation

The app is ready to run as a single Streamlit process when its bundled model, catalog, and resource CSV are present. Before hosting it, configure a writable durable location for `LEARNING_PROGRESS_FILE`; the default local JSON file is excluded from Git, is not authenticated, and is not suitable for multiple replicas without shared storage and application-level access controls. If using multiple app instances, mount the same catalog and snapshots on each instance or configure `SKILLSCOPE_JOB_CATALOG`, `SKILLSCOPE_DEMAND_CSV`, `SKILLSCOPE_DEMAND_METADATA`, and `SKILLSCOPE_TITLES_CSV` consistently.

The daily listing importer runs in GitHub Actions and needs `HEADCOUNT_API_KEY` as an Actions secret. The Streamlit app does not need that secret. The workflow publishes bounded category/skill and title aggregates with shared freshness metadata; it does not replace the model or job catalog. Review workflow permissions, secret availability, snapshot freshness, persistent storage, and the first-run sentence model download before a live demonstration or hosted rollout.

## Dataset

The GitHub repository currently contains a **3,200-row job catalog**, including approximately **1,000 Machine Learning Engineer rows**. This is the repository's compact catalog, not the separate 100,000-row catalog previously used in the development environment.

The bundled catalog currently contains **12 distinct normalized job titles** across five categories. The dashboard's **Explore job titles** section supports title search and category filtering, and the resume-analysis page offers those titles as selectable suggestions. The catalog has no per-record source timestamps and includes repeated/template descriptions, so its role list is a static dataset snapshot rather than a fresh or comprehensive view of the job market. Do not interpret catalog row totals as vacancies. The latest committed Headcount snapshot metadata records 10 API records at `2026-10-26T11:02:25Z`, which is too small to claim broad market coverage. That committed snapshot predates title aggregation and contains no listing titles.

The daily importer now publishes a second, title-only aggregate from distinct provider records. The dashboard labels these as recently observed provider titles, shows their generation time and limited sample counts, and marks stale data. Title aggregates include no descriptions, URLs, or personal details. They are discovery evidence only: recent title records do not gain invented skills and are not eligible for resume analysis unless they also appear in the skill-bearing bundled catalog. The existing model, scoring behavior, and saved progress remain unchanged.

Important data-quality note: the catalog contains repeated/template job descriptions and skill combinations. Row count must not be interpreted as the number of distinct real-world job vacancies. The daily data pipeline in `data_pipeline/` adds deduplication and quality-reporting foundations before any refreshed data is used by the app.

The app-compatible catalog columns are:

- `job_id`
- `category`
- `job_title`
- `job_description`
- `job_skill_set`

## Machine Learning Model

The current experiment uses a Gradient Boosting Regressor for compatibility-score prediction.

Reported evaluation on the experiment dataset:

- MAE: 9.3385
- RMSE: 12.2061
- R²: 0.7536

Input features include:

- Resume skill count
- Job skill count
- Skill overlap ratio
- TF-IDF similarity
- Semantic similarity

**Evaluation limitation:** the training target was derived from programmatically generated compatibility scores rather than independently human-annotated hiring outcomes. These metrics describe agreement with that constructed target; they do not establish real-world hiring prediction accuracy.

New, unlabelled job postings should not trigger model retraining. Retraining should wait until suitable labelled or human-reviewed examples are collected.

## Technologies Used

- Python, Pandas and NumPy
- Scikit-learn
- Sentence Transformers
- Joblib
- Streamlit
- Google Colab

## Application

The Streamlit application displays:

- Dashboard skill-demand summaries from the included job catalog and, when available, the latest aggregated India-listing snapshot
- Saved learning-plan and completed-step record totals from the local progress file
- Compatibility score
- Matched skills
- Missing skills
- Prioritized skill gaps
- Personalized learning roadmap
- Learning resources

The dashboard counts skill mentions in the catalog, which can include repeated/template rows; they are not vacancy counts. Recent listing counts are shown separately with their snapshot generation time. Saved progress totals cover local profiles and count a completed step again when it appears in a separate plan.

Recent listing zeros are meaningful only when a valid CSV and metadata sidecar are present. The dashboard reports the snapshot's checked API records, usable descriptions, matched category/skill pairs, generation time, and freshness. A valid snapshot with no rows is distinguished from a missing or malformed snapshot; a zero for a particular skill means it was not found in the limited sample, not that no jobs require it. Snapshots older than 36 hours are marked stale. **Reload dashboard data** clears Streamlit's cached data and rereads the catalog and snapshot already on disk; it does not contact Headcount or run an import. The daily workflow remains the supported source of new listing snapshots.

For plans saved after this update, progress records also store the roadmap step total, allowing the dashboard to show plan completion and a completion ratio based on persisted steps. Older records remain readable and their completed steps are preserved; they are marked as untracked until saved again with a step total. No completion percentage is inferred for those legacy records.

## Daily Data Pipeline

A daily Headcount Labs workflow fetches current, non-stale India listings published in the previous 48 hours, up to 250 distinct API records, including records without usable text. It uses descriptions in memory to count mentions of skills already present in the catalog taxonomy. It publishes category/skill counts, distinct normalized title counts, and a JSON run summary with record, processing, and time-window metadata; source descriptions, URLs, posting-level records, and personal details are never written to the repository. Recent title aggregates are discovery evidence only and do not add skill records to resume analysis.

The Streamlit app shows skill counts as a supplementary recent-listing signal and title counts in a separate recent-title discovery section. The trained model and job_catalog.csv remain unchanged. The workflow stores aggregates in data_pipeline/headcount_skill_demand.csv and data_pipeline/headcount_job_titles.csv, shares freshness metadata in data_pipeline/headcount_skill_demand.metadata.json, runs importer tests, and uploads a 14-day artifact. If the API request or safety checks fail, the existing app catalog remains available.

The first live GitHub Actions run succeeded on 2026-10-24. API use is bounded to 250 delivered records per run; account-level allowances and any other Headcount API usage are shared.

## Current Status

The app remains a prototype. Its compatibility score is trained against a programmatically generated target, not independently labeled hiring outcomes. The pipeline now adds a fresh, limited-window market signal without retraining the model or replacing the catalog.

## Learning Progress and Deployment

After analyzing a resume, mark roadmap steps complete and select **Save progress**. Progress is stored in `data/learning_progress.json` by default. The file is excluded from Git. Set `LEARNING_PROGRESS_FILE` to use another writable local path. A normalized profile label is hashed before it is saved; the raw label and resume contents are not stored in the progress file. Profile labels only separate local records and do not provide authentication or access control. Use a nickname rather than an email address or other sensitive identifier.

The JSON file is written atomically and malformed or unsupported files are left unchanged. This file-based option is suitable for local use or a single app process with durable disk. Many hosted Streamlit environments use ephemeral filesystems, and multiple replicas may have separate files; progress can disappear on restart or differ between replicas. Before deploying there, configure `LEARNING_PROGRESS_FILE` to a durable shared store or replace the file adapter with an authenticated database-backed store. Do not treat the default file as multi-user private storage.

The dashboard source paths may be overridden with `SKILLSCOPE_JOB_CATALOG`, `SKILLSCOPE_DEMAND_CSV`, and `SKILLSCOPE_DEMAND_METADATA`. Keep these files available to every app instance. A manual dashboard reload only sees files mounted in the current instance; deploy the published daily snapshot or provide a shared durable mount to keep replicas consistent. The current file-backed progress store is also local to each instance unless configured on shared durable storage.


