# Intelligent Skill Gap Analysis

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

The app is ready to run as a single Streamlit process when its bundled model, catalog, and resource CSV are present. Before hosting it, configure a writable durable location for `LEARNING_PROGRESS_FILE`; the default local JSON file is excluded from Git, is not authenticated, and is not suitable for multiple replicas without shared storage and application-level access controls. If using multiple app instances, mount the same catalog and demand snapshot on each instance or configure `SKILLSCOPE_JOB_CATALOG`, `SKILLSCOPE_DEMAND_CSV`, and `SKILLSCOPE_DEMAND_METADATA` consistently.

The daily listing importer runs in GitHub Actions and needs `HEADCOUNT_API_KEY` as an Actions secret. The Streamlit app does not need that secret. The workflow publishes only bounded category/skill aggregates and metadata; it does not replace the model or job catalog. Review workflow permissions, secret availability, snapshot freshness, persistent storage, and the first-run sentence model download before a live demonstration or hosted rollout.

## Dataset

The GitHub repository currently contains a **3,200-row job catalog**, including approximately **1,000 Machine Learning Engineer rows**. This is the repository's compact catalog, not the separate 100,000-row catalog previously used in the development environment.

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

A daily Headcount Labs workflow fetches current, non-stale India listings published in the previous 48 hours, up to 250 distinct API records, including records without usable text. It uses descriptions in memory to count mentions of skills already present in the catalog taxonomy. It publishes category/skill counts and a JSON run summary with record, processing, and time-window metadata; source descriptions and personal details are never written to the repository.

The Streamlit app shows those counts as a supplementary recent-listing signal beside its existing catalog demand. The trained model and job_catalog.csv remain unchanged. The workflow stores the aggregate in data_pipeline/headcount_skill_demand.csv and its metadata in data_pipeline/headcount_skill_demand.metadata.json, runs the importer tests, and uploads a 14-day artifact. If the API request or safety checks fail, the existing app catalog remains available.

The first live GitHub Actions run succeeded on 2026-10-24. API use is bounded to 250 delivered records per run; account-level allowances and any other Headcount API usage are shared.

## Current Status

The app remains a prototype. Its compatibility score is trained against a programmatically generated target, not independently labeled hiring outcomes. The pipeline now adds a fresh, limited-window market signal without retraining the model or replacing the catalog.

## Learning Progress and Deployment

After analyzing a resume, mark roadmap steps complete and select **Save progress**. Progress is stored in `data/learning_progress.json` by default. The file is excluded from Git. Set `LEARNING_PROGRESS_FILE` to use another writable local path. A normalized profile label is hashed before it is saved; the raw label and resume contents are not stored in the progress file. Profile labels only separate local records and do not provide authentication or access control. Use a nickname rather than an email address or other sensitive identifier.

The JSON file is written atomically and malformed or unsupported files are left unchanged. This file-based option is suitable for local use or a single app process with durable disk. Many hosted Streamlit environments use ephemeral filesystems, and multiple replicas may have separate files; progress can disappear on restart or differ between replicas. Before deploying there, configure `LEARNING_PROGRESS_FILE` to a durable shared store or replace the file adapter with an authenticated database-backed store. Do not treat the default file as multi-user private storage.

The dashboard source paths may be overridden with `SKILLSCOPE_JOB_CATALOG`, `SKILLSCOPE_DEMAND_CSV`, and `SKILLSCOPE_DEMAND_METADATA`. Keep these files available to every app instance. A manual dashboard reload only sees files mounted in the current instance; deploy the published daily snapshot or provide a shared durable mount to keep replicas consistent. The current file-backed progress store is also local to each instance unless configured on shared durable storage.

