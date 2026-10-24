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

- Compatibility score
- Matched skills
- Missing skills
- Prioritized skill gaps
- Personalized learning roadmap
- Learning resources

## Daily Data Pipeline

A daily Headcount Labs workflow fetches current, non-stale India listings published in the previous 48 hours, up to 250 distinct API records, including records without usable text. It uses descriptions in memory to count mentions of skills already present in the catalog taxonomy. It publishes category/skill counts and a JSON run summary with record, processing, and time-window metadata; source descriptions and personal details are never written to the repository.

The Streamlit app shows those counts as a supplementary recent-listing signal beside its existing catalog demand. The trained model and job_catalog.csv remain unchanged. The workflow stores the aggregate in data_pipeline/headcount_skill_demand.csv and its metadata in data_pipeline/headcount_skill_demand.metadata.json, runs the importer tests, and uploads a 14-day artifact. If the API request or safety checks fail, the existing app catalog remains available.

The first live GitHub Actions run succeeded on 2026-10-24. API use is bounded to 250 delivered records per run; account-level allowances and any other Headcount API usage are shared.

## Current Status

The app remains a prototype. Its compatibility score is trained against a programmatically generated target, not independently labeled hiring outcomes. The pipeline now adds a fresh, limited-window market signal without retraining the model or replacing the catalog.
