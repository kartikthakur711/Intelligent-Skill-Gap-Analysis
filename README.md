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

The notebook uses a seeded 80/20 random split (`random_state=42`) and reports metrics after clipping predictions to 0–100. It compares Random Forest and Gradient Boosting on the same holdout and selects the lower-MAE model there, so this split is a model-selection validation set rather than an untouched final test set. The reported values above are the existing project results; CI does not retrain the model or claim to reproduce those metrics.

`model_evaluation.py` evaluates the saved model on an independently labelled holdout with the same clipping and MAE/RMSE/R² definitions. It never fits or saves a model. The `Model and app validation` workflow checks the saved artifact contract, representative finite predictions, additive explanations, holdout metric calculations, and initial Streamlit rendering. An independently labelled holdout is not currently included in the repository, so real-world/generalization performance remains unverified.

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

The daily pipeline is in `data_pipeline/`.

It currently provides:
- A documented ingestion design and safety rules
- A catalog deduplication utility
- A JSON quality report with unique-posting skill counts

The bounded Headcount importer and scheduled GitHub Actions workflow publish aggregate skill-demand artifacts; source descriptions are not included in those outputs. Demand counts guide skill-gap priority only and are not used to retrain the saved model.

## Current Status

The `feature/daily-job-data-pipeline` branch includes the explainability and saved-model validation work. The trained model is validated as a runtime artifact but is not retrained by these checks. The `main` branch and saved model remain unchanged by this phase.
