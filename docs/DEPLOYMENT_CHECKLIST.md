# Deployment checklist

Deployment has not been confirmed. Complete the items that apply to the intended hosting environment and record who verified them.

## Application readiness

- [ ] Choose a hosting environment and document its owner, region, availability target, and rollback procedure.
- [ ] Use Python 3.11 and install the repository dependencies from `requirements.txt`.
- [ ] Confirm `resume_job_ml_model.pkl`, `job_catalog.csv`, and `learning_resources.csv` are present in the deployed release. Keep the model artifact unchanged unless a separately reviewed model release is approved.
- [ ] Confirm outbound access for first-use download of `all-MiniLM-L6-v2`; if `job_catalog.csv` is absent, the app attempts a Hugging Face dataset download. Prefer packaging and validating the intended catalog/model resources in the release.
- [ ] Launch with `streamlit run app.py` and check a text PDF, DOCX, and TXT upload, unsupported-file handling, no-match titles, and a representative matched title.
- [ ] Verify that resumes and extracted text are not retained or exposed through application logs, temporary storage, analytics, or backups beyond the approved policy.
- [ ] Confirm upload limits, authentication, authorization, TLS, secrets handling, and abuse controls for the chosen host.
- [ ] Provide user-facing context that skill extraction can miss/overmatch terms and that the compatibility score is not a hiring decision or validated measure of candidate suitability.

## Model and evaluation readiness

- [ ] Preserve the current saved model; this documentation/deployment phase does not retrain or overwrite it.
- [ ] Keep the reported MAE/RMSE/R² labelled as agreement with programmatically generated targets on a model-selection split.
- [ ] Before making predictive-validity claims, define a human scoring rubric, collect independent reviewed examples, measure reviewer agreement, and hold a separate final evaluation set untouched during tuning.
- [ ] Keep personal resume/job identifiers and reviewer notes in an access-controlled store; do not commit them to the repository.
- [ ] Review subgroup coverage, uncertainty, and potential disparate impact before using results in consequential settings.

## Optional daily skill-demand workflow

- [ ] Decide whether this separate aggregate workflow is needed; it is not required to run the Streamlit app.
- [ ] Review Headcount API access, allowance, applicable terms, and third-party job-board rights for the intended use.
- [ ] Add `HEADCOUNT_API_KEY` as a GitHub Actions secret; never put it in a file, command history, or artifact.
- [ ] Run the workflow manually and confirm the import finishes, the report contains only aggregate `category`, `skill`, and `distinct_job_count` fields, and the artifact has the expected 14-day retention.
- [ ] Confirm the current 250-unique-job cap and 48-hour lookback are suitable; a run exceeding the cap fails and requires an explicit configuration/review change.
- [ ] Confirm whether scheduled execution is intended. GitHub schedules run from the default branch; make sure the workflow file is on that branch and its explicit checkout of `feature/daily-job-data-pipeline` points to the intended implementation.
- [ ] Assign an owner to inspect failed runs and artifact quality. The app currently does not read this artifact; do not describe it as app demand data until that integration is implemented and reviewed.

## Release verification

- [ ] Review the exact branch and commit being released; the documentation phase is scoped to `feature/daily-job-data-pipeline`.
- [ ] Confirm the Model and app validation workflow passes for code changes that trigger it. The recorded run #2 on `67cd4c5` is a historical software-validation result, not a deployment or predictive evaluation.
- [ ] Complete the relevant checks above, record dates and owners, and publish the deployment status only after the host is actually configured and smoke-checked.
- [ ] Define monitoring for availability, exceptions, dependency/model compatibility, data freshness when the optional pipeline is enabled, and a rollback path.
