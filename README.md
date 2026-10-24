# Intelligent Skill Gap Analysis

A Streamlit prototype that compares resume text with a selected job from a bundled catalog, estimates a compatibility score with a saved regression model, identifies skill gaps, and suggests a learning sequence and resources.

This repository contains both the app and a separate daily skill-demand aggregation workflow. The daily artifact does not update the app catalog or retrain the model.

## Architecture and workflow

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the component diagram, data flow, and GitHub Actions behavior.

## Run locally

Requires Python 3.11 (the validation and daily-data workflows use Python 3.11). From the repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit. Upload a text-based PDF, DOCX, or TXT resume and enter a target job title. The app loads `job_catalog.csv`, `learning_resources.csv`, and `resume_job_ml_model.pkl` from the repository directory. If the catalog or resources file is absent, the app has fallback behavior: it downloads the Hugging Face job dataset for the catalog, or uses a small in-code resource list. Sentence Transformers loads `all-MiniLM-L6-v2` on first use, which may require network access and downloads the model into the local model cache.

The saved model is a runtime artifact. Normal app use and validation do not train or save a replacement model.

## Dependencies

Install the versions/ranges declared in [`requirements.txt`](requirements.txt): Streamlit, Pandas, NumPy, scikit-learn (pinned to 1.6.1 for saved-artifact compatibility), Joblib, Sentence Transformers, Hugging Face Datasets, pypdf, and python-docx. The daily importer uses the Python standard library; its workflow does not install the full app requirements. CI installs the smaller set needed for model/app validation.

## Data and configuration

The checked-in `job_catalog.csv` has 3,200 rows and the app uses `job_id`, `category`, `job_title`, `job_description`, and `job_skill_set`. Repeated/template rows and skill combinations exist, so row count is not a count of distinct vacancies. The app's displayed gap priority is based on skill frequency across catalog rows; it is not distinct-posting demand and does not use the Headcount artifact.

The optional daily workflow is configured in [`.github/workflows/daily-job-data.yml`](.github/workflows/daily-job-data.yml). It calls the bounded Headcount Labs importer for current India postings updated in the prior 48 hours, processes at most 250 unique job IDs per run, and matches title/description text against the existing catalog skill taxonomy. It requires the GitHub Actions secret `HEADCOUNT_API_KEY`. The workflow writes only `category`, `skill`, and `distinct_job_count` aggregates to a GitHub Actions artifact retained for 14 days; fetched posting text is not written to the artifact or committed. The pipeline does not refresh `job_catalog.csv`, feed its output into the app, or retrain the model. More details and limits are in [`data_pipeline/README.md`](data_pipeline/README.md).

## Model and evaluation limits

The saved model is a Gradient Boosting Regressor using five inputs: resume skill count, job skill count, skill overlap ratio, TF-IDF similarity, and semantic similarity. The notebook reports MAE 9.3385, RMSE 12.2061, and R² 0.7536 on its seeded 80/20 split. The notebook compares Random Forest and Gradient Boosting on the same holdout and selects by holdout MAE, so that split is a model-selection validation set, not an untouched final test set.

The training target was programmatically generated. These metrics measure agreement with that constructed target and do not establish predictive validity for hiring outcomes or candidate suitability. There is no independent human-labelled holdout in the repository. [`evaluation/README.md`](evaluation/README.md) documents how to collect and evaluate one. `model_evaluation.py` evaluates a supplied independently labelled holdout with the saved model; it never fits or saves a model. Do not treat software checks or app rendering as predictive evaluation.

App limitations include vocabulary-based resume skill extraction, approximate job-title retrieval, and reliance on a small, repetitive catalog. The score is a model estimate, clipped to 0–100 for display; feature attributions explain model behavior and are not causal effects or hiring decisions. Human review is needed before using results for consequential decisions.

## Testing status

The GitHub Actions **Model and app validation** workflow passed run **#2** on commit [`67cd4c5`](https://github.com/kartikthakur711/Intelligent-Skill-Gap-Analysis/commit/67cd4c555a2ec16bf44a5f091535df323e4801a7), as recorded for this phase. The workflow checks the saved model/vectorizer contract, representative finite predictions, additive explanations, holdout metric validation behavior, unit tests, and initial Streamlit rendering. It does not train the model or measure predictive validity. The workflow is triggered manually, on selected app/model/test changes pushed to `feature/daily-job-data-pipeline`, and for matching pull requests targeting `main`.

To run checks locally:

```powershell
python -B -m unittest discover -s tests -v
python -B -m unittest discover -s data_pipeline -p 'test_*.py' -v
```

The initial Streamlit render check is included in the model validation workflow. Live Headcount API access, its credential, and scheduled artifact generation have not been confirmed by the validation run described above.

## Deployment

Deployment is not yet established by this repository. Use the [deployment checklist](docs/DEPLOYMENT_CHECKLIST.md) before exposing the app or enabling the scheduled data workflow. In particular, configure and verify the API secret only if the separate data workflow is needed, and confirm privacy, data rights, hosting, and operational ownership for the intended deployment.
