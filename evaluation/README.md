# Phase 8 — Model Evaluation Protocol

This folder contains the input template and protocol for evaluating the **existing saved model** on an independently labelled holdout set.

## Important limitation

The training notebook generated its target compatibility scores programmatically. The historical MAE/RMSE/R² values therefore measure agreement with that constructed target; they are **not** evidence of real-world hiring or candidate suitability accuracy.

No human-labelled holdout examples are included in this repository. Do not fill the template with guessed labels or reuse the generated training targets and call them independent ground truth.

## Holdout CSV format

Start from `holdout_template.csv`. Add one row per independently reviewed resume–job pair.

Required columns:

- `resume_skill_count`
- `job_skill_count`
- `skill_overlap_ratio`
- `tfidf_similarity`
- `semantic_similarity`
- `human_compatibility_score`

The first five columns must be generated with the same preprocessing and feature definitions used by the app. The final column must be a human-assigned score from 0 to 100, using a written rubric agreed by reviewers. Keep the resume/job pair IDs and reviewer notes in a separately access-controlled file; do not commit personal resumes or identifiable candidate data.

## Evaluation

Once enough independent labels exist, load the saved artifact and call:

```python
import joblib
import pandas as pd
from model_evaluation import evaluate_saved_model

data = pd.read_csv("evaluation/holdout.csv")
artifacts = joblib.load("resume_job_ml_model.pkl")
features = data[[
    "resume_skill_count",
    "job_skill_count",
    "skill_overlap_ratio",
    "tfidf_similarity",
    "semantic_similarity",
]]
metrics = evaluate_saved_model(
    artifacts["model"],
    features,
    data["human_compatibility_score"],
)
print(metrics)
```

Report sample count, label rubric, reviewer agreement, sampling method, and MAE/RMSE/R². Report uncertainty or subgroup results when sample size permits. Keep this holdout untouched during model selection; if it is used to tune the model, it is no longer a final test set.

## Safety rules

- Do not retrain or overwrite `resume_job_ml_model.pkl` as part of this evaluation.
- Do not use unlabelled job-posting volume as a compatibility target.
- Do not report CI smoke-test results as evidence of predictive validity.
- Preserve the distinction between app smoke tests, software unit tests, and independent predictive evaluation.
