import ast
import difflib
import hashlib
import io
import os
import html
import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.metrics.pairwise import cosine_similarity

from data_pipeline.skill_demand import load_headcount_demand as read_headcount_demand
from data_pipeline.skill_demand import load_headcount_titles as read_headcount_titles
from data_pipeline.skill_demand import recent_skill_counts
from app_helpers import (
    build_dashboard_skill_demand,
    build_learning_plan,
    build_learning_roadmap,
    build_skill_recommendations,
    clean_html,
    summarize_recent_snapshot,
)
from learning_progress import ProgressStoreError, load_progress, save_progress, summarize_progress
from dashboard_ui import apply_app_styles, render_dashboard, render_sidebar, render_skill_chips
from role_discovery import catalog_roles


APP_DIR = Path(__file__).resolve().parent
MODEL_FILE = APP_DIR / "resume_job_ml_model.pkl"
JOB_FILE = Path(os.environ.get("SKILLSCOPE_JOB_CATALOG", APP_DIR / "job_catalog.csv"))
RESOURCE_FILE = APP_DIR / "learning_resources.csv"
HEADCOUNT_DEMAND_FILE = Path(os.environ.get("SKILLSCOPE_DEMAND_CSV", APP_DIR / "data_pipeline" / "headcount_skill_demand.csv"))
HEADCOUNT_METADATA_FILE = Path(os.environ.get("SKILLSCOPE_DEMAND_METADATA", APP_DIR / "data_pipeline" / "headcount_skill_demand.metadata.json"))
HEADCOUNT_TITLES_FILE = Path(os.environ.get("SKILLSCOPE_TITLES_CSV", APP_DIR / "data_pipeline" / "headcount_job_titles.csv"))
LEARNING_PROGRESS_FILE = Path(
    os.environ.get("LEARNING_PROGRESS_FILE", APP_DIR / "data" / "learning_progress.json")
)


def clean_job_description(text):
    """Remove HTML markup/entities from dataset job descriptions for display and NLP."""
    text = "" if text is None else str(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


st.set_page_config(
    page_title="Intelligent Skill Gap Analysis",
    page_icon="🎯",
    layout="wide",
)
apply_app_styles()



# -----------------------------
# Helpers
# -----------------------------
def normalize_skill(skill):
    skill = str(skill).lower().strip()
    skill = skill.replace(".", "")
    skill = skill.replace("-", " ")
    skill = " ".join(skill.split())

    aliases = {
        "scikit learn": "scikit learn",
        "scikit-learn": "scikit learn",
        "auto cad": "autocad",
        "autocad": "autocad",
        "tensorflow keras": "tensorflow",
        "mysql database": "mysql",
        "r or java": "r or java",
    }
    return aliases.get(skill, skill)


def parse_list(value):
    if isinstance(value, list):
        return value
    if pd.isna(value):
        return []
    text = str(value).strip()
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except Exception:
        pass
    return [x.strip() for x in re.split(r"[,;|]", text) if x.strip()]


def skill_match(resume_skill, job_skill):
    r = normalize_skill(resume_skill)
    j = normalize_skill(job_skill)
    if r == j:
        return True
    if j == "r or java" and r in {"r", "java"}:
        return True
    return False


def calculate_matches(resume_skills, job_skills):
    # Display the canonical job-skill label once, rather than every resume spelling variant.
    matches = []
    seen = set()
    for js in job_skills:
        key = normalize_skill(js)
        if key in seen:
            continue
        if any(skill_match(rs, js) for rs in resume_skills):
            matches.append(js)
            seen.add(key)
    return matches


def calculate_gap(resume_skills, job_skills):
    gap = []
    seen = set()
    for js in job_skills:
        key = normalize_skill(js)
        if key in seen:
            continue
        if not any(skill_match(rs, js) for rs in resume_skills):
            gap.append(js)
            seen.add(key)
    return gap


def extract_text_from_upload(uploaded_file):
    suffix = Path(uploaded_file.name).suffix.lower()
    data = uploaded_file.getvalue()

    if suffix == ".txt":
        return data.decode("utf-8", errors="ignore")

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as exc:
            raise RuntimeError(f"Could not read PDF: {exc}")

    if suffix == ".docx":
        try:
            from docx import Document
            doc = Document(io.BytesIO(data))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception as exc:
            raise RuntimeError(f"Could not read DOCX: {exc}")

    raise RuntimeError("Unsupported file type. Upload PDF, DOCX, or TXT.")


@st.cache_resource
def load_model():
    if not MODEL_FILE.exists():
        return None
    return joblib.load(MODEL_FILE)


@st.cache_resource
def load_sentence_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("all-MiniLM-L6-v2")


@st.cache_data
def load_job_catalog():
    if JOB_FILE.exists():
        df = pd.read_csv(JOB_FILE)
    else:
        from datasets import load_dataset
        ds = load_dataset("batuhanmtl/job-skill-set", split="train")
        df = ds.to_pandas()
        keep = ["job_id", "category", "job_title", "job_description", "job_skill_set"]
        df = df[keep].copy()
        df.to_csv(JOB_FILE, index=False)

    if "job_title_normalized" not in df.columns:
        df["job_title_normalized"] = df["job_title"].astype(str).str.lower().str.strip()

    df["job_description"] = (
        df["job_description"]
        .fillna("")
        .map(clean_html)
    )

    df["skills_list"] = df["job_skill_set"].apply(parse_list)
    return df


@st.cache_data
def load_resources():
    if RESOURCE_FILE.exists():
        return pd.read_csv(RESOURCE_FILE)
    # Fallback keeps the demo usable if the CSV was not uploaded.
    fallback = [
        ["python", "Python Documentation", "Documentation", "https://docs.python.org/3/"],
        ["numpy", "NumPy Documentation", "Documentation", "https://numpy.org/doc/"],
        ["pandas", "Pandas Documentation", "Documentation", "https://pandas.pydata.org/docs/"],
        ["scikit learn", "Scikit-learn User Guide", "Documentation", "https://scikit-learn.org/stable/user_guide.html"],
        ["salesforce", "Salesforce Developer Documentation", "Documentation", "https://developer.salesforce.com/docs"],
        ["apex", "Apex Developer Guide", "Documentation", "https://developer.salesforce.com/docs/atlas.en-us.apexcode.meta/apexcode/"],
        ["soap apis", "Salesforce SOAP API Developer Guide", "Documentation", "https://developer.salesforce.com/docs/atlas.en-us.api.meta/api/"],
        ["rest apis", "MDN HTTP Overview", "Documentation", "https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview"],
        ["docker", "Docker Get Started", "Tutorial", "https://docs.docker.com/get-started/"],
        ["git", "Git Documentation", "Documentation", "https://git-scm.com/doc"],
    ]
    return pd.DataFrame(fallback, columns=["skill", "resource", "type", "url"])



def load_headcount_demand():
    """Load derived counts only; source postings are never read by the app."""
    return read_headcount_demand(HEADCOUNT_DEMAND_FILE, normalize_skill, HEADCOUNT_METADATA_FILE)


def load_headcount_titles():
    """Load only a validated title aggregate and the shared listing metadata."""
    return read_headcount_titles(HEADCOUNT_TITLES_FILE, HEADCOUNT_METADATA_FILE)

def extract_resume_skills(resume_text, skill_vocabulary):
    text = resume_text.lower()
    found = []
    normalized_text = re.sub(r"[^a-z0-9+#.\-/ ]", " ", text)
    normalized_text = " ".join(normalized_text.split())

    # Longer skills first to reduce partial matches.
    for skill in sorted(skill_vocabulary, key=len, reverse=True):
        ns = normalize_skill(skill)
        if not ns:
            continue
        pattern = r"(?<![a-z0-9])" + re.escape(ns) + r"(?![a-z0-9])"
        if re.search(pattern, normalized_text):
            found.append(skill)

    # Common aliases that may occur in resumes.
    alias_patterns = {
        "scikit learn": ["scikit-learn", "scikit learn", "sklearn"],
        "c++": ["c++"],
        "c#": ["c#", "c sharp"],
        "javascript": ["javascript", "java script"],
        "machine learning": ["machine learning", "ml"],
        "deep learning": ["deep learning", "dl"],
    }
    for canonical, variants in alias_patterns.items():
        if any(re.search(r"(?<![a-z0-9])" + re.escape(v) + r"(?![a-z0-9])", text) for v in variants):
            found.append(canonical)

    return list(dict.fromkeys(found))


def normalize_job_title(title):
    title = str(title).lower().strip()
    title = re.sub(r"[^a-z0-9+# ]", " ", title)
    title = " ".join(title.split())

    aliases = {
        "ml engineer": "machine learning engineer",
        "ml developer": "machine learning developer",
        "ai engineer": "artificial intelligence engineer",
        "software developer": "software engineer",
        "application developer": "software developer",
    }
    return aliases.get(title, title)


def title_informative_tokens(title):
    generic = {
        "engineer", "developer", "developers", "senior", "junior", "sr",
        "jr", "lead", "principal", "associate", "specialist", "consultant",
        "manager", "architect", "professional", "intern", "trainee", "ii", "iii"
    }
    return {t for t in normalize_job_title(title).split() if t not in generic}


@st.cache_data(show_spinner=False)
def get_title_embeddings(title_texts):
    model = load_sentence_model()
    return model.encode(list(title_texts), normalize_embeddings=True, show_progress_bar=False)


def choose_job(job_title, catalog, sentence_model=None):
    """Conservative job-title retrieval: never force an unrelated role."""
    query = job_title.strip()
    query_norm = normalize_job_title(query)
    if not query_norm:
        return None, [], 0.0, "none"

    normalized_catalog = catalog["job_title"].map(normalize_job_title)

    # 1. Exact normalized title.
    exact = catalog[normalized_catalog == query_norm]
    if not exact.empty:
        return exact.iloc[0], [], 1.0, "exact"

    q_tokens = title_informative_tokens(query)
    if not q_tokens:
        return None, [], 0.0, "none"

    # 2. Require all informative query terms for a strong token match.
    rows = []
    for idx, title in catalog["job_title"].items():
        c_tokens = title_informative_tokens(title)
        overlap = q_tokens.intersection(c_tokens)
        recall = len(overlap) / len(q_tokens) if q_tokens else 0.0
        precision = len(overlap) / len(c_tokens) if c_tokens else 0.0
        f1 = 2 * recall * precision / (recall + precision) if recall + precision else 0.0
        rows.append((idx, title, recall, precision, f1))

    scores_df = pd.DataFrame(rows, columns=["idx", "title", "recall", "precision", "f1"])
    strong = scores_df[scores_df["recall"] >= 1.0].copy()

    if not strong.empty:
        if sentence_model is not None and len(strong) > 1:
            q_emb = sentence_model.encode([query], normalize_embeddings=True, show_progress_bar=False)
            c_emb = sentence_model.encode(strong["title"].tolist(), normalize_embeddings=True, show_progress_bar=False)
            semantic = np.dot(c_emb, q_emb[0])
            strong["semantic"] = semantic
            best = strong.sort_values(["semantic", "f1"], ascending=False).iloc[0]
            relevance = float(np.clip((best["semantic"] + 1) / 2, 0, 1))
        else:
            best = strong.sort_values("f1", ascending=False).iloc[0]
            relevance = 0.85
        row = catalog.loc[int(best["idx"])]
        return row, strong["title"].head(5).tolist(), relevance, "strong-token"

    # 3. Semantic fallback, but only when the candidate shares at least half
    # of the informative terms and has genuinely high semantic similarity.
    if sentence_model is not None:
        titles = catalog["job_title"].astype(str).tolist()
        title_emb = get_title_embeddings(tuple(titles))
        q_emb = sentence_model.encode([query], normalize_embeddings=True, show_progress_bar=False)
        semantic_scores = np.dot(title_emb, q_emb[0])
        best_idx = int(np.argmax(semantic_scores))
        best_row = catalog.iloc[best_idx]
        best_score = float(np.clip((semantic_scores[best_idx] + 1) / 2, 0, 1))
        best_tokens = title_informative_tokens(best_row["job_title"])
        token_recall = len(q_tokens.intersection(best_tokens)) / len(q_tokens)

        if best_score >= 0.72 and token_recall >= 0.5:
            return best_row, [best_row["job_title"]], best_score, "semantic"

    # 4. Conservative fuzzy fallback with an overlap gate.
    titles = catalog["job_title"].astype(str).tolist()
    close = difflib.get_close_matches(query, titles, n=5, cutoff=0.70)
    for title in close:
        title_tokens = title_informative_tokens(title)
        overlap = len(q_tokens.intersection(title_tokens)) / len(q_tokens)
        if overlap >= 0.5:
            row = catalog[catalog["job_title"] == title].iloc[0]
            return row, close, 0.70, "fuzzy"

    return None, [], 0.0, "none"


def priority_from_demand(missing_skills, catalog, recent_counts=None):
    counter = {}
    for skills in catalog["skills_list"]:
        for skill in skills:
            key = normalize_skill(skill)
            counter[key] = counter.get(key, 0) + 1

    max_demand = max(counter.values(), default=1)
    rows = []
    for skill in missing_skills:
        count = counter.get(normalize_skill(skill), 0)
        score = count / max_demand
        priority = "High" if score >= 0.50 else "Medium" if score >= 0.20 else "Low"
        row = {
            "Skill": skill,
            "Job Demand": count,
            "Demand Score": round(score, 3),
            "Priority": priority,
        }
        if recent_counts is not None:
            row["Recent India Listings (48h)"] = int(recent_counts.get(normalize_skill(skill), 0))
        rows.append(row)
    return pd.DataFrame(rows).sort_values("Demand Score", ascending=False) if rows else pd.DataFrame()


# -----------------------------
# UI
# -----------------------------
page = render_sidebar()
if page == "Dashboard":
    dashboard_roles = []
    dashboard_recent_titles = None
    dashboard_title_metadata = None
    dashboard_title_status = summarize_recent_snapshot(None, None)
    dashboard_demand = []
    dashboard_demand_metadata = None
    dashboard_snapshot_status = summarize_recent_snapshot(None, None)
    dashboard_recent_counts = None
    dashboard_recent_demand = []
    try:
        dashboard_catalog = load_job_catalog()
        dashboard_roles = catalog_roles(dashboard_catalog)
        dashboard_demand = build_dashboard_skill_demand(
            dashboard_catalog["skills_list"].tolist(), None, normalize_skill
        )
    except Exception:
        # Keep the landing page available if an optional data source is unavailable.
        dashboard_demand = []
    try:
        dashboard_headcount_rows, dashboard_demand_metadata = load_headcount_demand()
        dashboard_recent_counts = recent_skill_counts(dashboard_headcount_rows)
        dashboard_snapshot_status = summarize_recent_snapshot(dashboard_headcount_rows, dashboard_demand_metadata)
        all_dashboard_demand = build_dashboard_skill_demand(
            dashboard_catalog["skills_list"].tolist(), dashboard_recent_counts, normalize_skill, limit=1000
        )
        dashboard_demand = all_dashboard_demand[:5]
        dashboard_recent_demand = sorted(
            (row for row in all_dashboard_demand if row.get("Recent India listings", 0) > 0),
            key=lambda row: (-row["Recent India listings"], normalize_skill(row["Skill"])),
        )[:5]
    except Exception:
        # Keep catalog summaries available if only the optional snapshot is unavailable.
        dashboard_snapshot_status = summarize_recent_snapshot(None, None)
        dashboard_recent_demand = []
        if dashboard_demand:
            dashboard_demand = build_dashboard_skill_demand(
                dashboard_catalog["skills_list"].tolist(), None, normalize_skill
            )
    try:
        dashboard_recent_titles, dashboard_title_metadata = load_headcount_titles()
        dashboard_title_status = summarize_recent_snapshot(dashboard_recent_titles, dashboard_title_metadata)
    except Exception:
        dashboard_recent_titles, dashboard_title_metadata = None, None
        dashboard_title_status = summarize_recent_snapshot(None, None)
    dashboard_progress = None
    dashboard_progress_error = ""
    try:
        dashboard_progress = summarize_progress(LEARNING_PROGRESS_FILE)
    except ProgressStoreError as exc:
        dashboard_progress_error = str(exc)
    render_dashboard(
        dashboard_demand,
        dashboard_demand_metadata,
        dashboard_progress,
        dashboard_progress_error,
        dashboard_snapshot_status,
        dashboard_recent_demand,
        dashboard_roles,
        dashboard_recent_titles,
        dashboard_title_metadata,
        dashboard_title_status,
    )
else:
    st.markdown('<div class="analysis-kicker">Resume matching</div>', unsafe_allow_html=True)
    st.markdown('<div class="analysis-title">See how your skills line up.</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="analysis-copy">Choose a role, add your resume, and get a clear view of your strengths and next learning steps.</div>',
        unsafe_allow_html=True,
    )
    try:
        available_roles = [role["Job title"] for role in catalog_roles(load_job_catalog())]
    except Exception:
        available_roles = []

    with st.container(border=True):
        st.markdown('<div class="section-title">Start your analysis</div>', unsafe_allow_html=True)
        st.caption("Your resume is analyzed in this session and is not saved with learning progress.")
        upload_col, role_col = st.columns([1.05, 0.95], gap="large")
        with upload_col:
            st.markdown('<div class="analysis-step"><span>1</span> Add your resume</div>', unsafe_allow_html=True)
            uploaded = st.file_uploader("Resume file", type=["pdf", "docx", "txt"], label_visibility="collapsed")
            st.caption("PDF, Word, or text file · Text-based PDFs work best")
            if uploaded is not None:
                st.success(f"Resume ready · {uploaded.name}")
        with role_col:
            st.markdown('<div class="analysis-step"><span>2</span> Choose your target role</div>', unsafe_allow_html=True)
            selected_role = st.selectbox(
                "Browse available catalog titles",
                [""] + available_roles,
                format_func=lambda value: "Choose a title from the catalog" if not value else value,
                key="analysis_catalog_role",
                on_change=lambda: st.session_state.__setitem__("target_job_title", st.session_state["analysis_catalog_role"]),
            )
            if "target_job_title" not in st.session_state:
                st.session_state["target_job_title"] = selected_role
            job_title = st.text_input(
                "Target Job Title",
                placeholder="e.g., Data Scientist",
                help="Choose a catalog title above or enter another role to try conservative matching.",
                key="target_job_title",
            )
        analyze = st.button("Analyze my resume  →", type="primary", use_container_width=True)

    input_fingerprint = ""
    if uploaded is not None and job_title.strip():
        input_fingerprint = hashlib.sha256(
            uploaded.getvalue() + b"\0" + job_title.strip().casefold().encode("utf-8")
        ).hexdigest()
    if analyze and input_fingerprint:
        st.session_state["analysis_input_fingerprint"] = input_fingerprint
    should_analyze = bool(input_fingerprint) and (
        st.session_state.get("analysis_input_fingerprint") == input_fingerprint
    ) or analyze

    if should_analyze:
        if uploaded is None:
            st.error("Please upload a resume.")
            st.stop()
        if not job_title.strip():
            st.error("Please enter a target job title.")
            st.stop()

        try:
            resume_text = extract_text_from_upload(uploaded)
            if len(resume_text.strip()) < 50:
                st.error("Very little text was extracted from the resume. Try a text-based PDF/DOCX.")
                st.stop()

            catalog = load_job_catalog()
            sentence_model = load_sentence_model()
            selected_job, suggestions, title_score, match_method = choose_job(
                job_title, catalog, sentence_model
            )
            if selected_job is None:
                st.error("No sufficiently relevant job title was found in the job-description dataset.")
                st.info("Try a more specific title such as Machine Learning Engineer, Data Scientist, or Software Engineer.")
                st.stop()

            if match_method == "exact":
                st.success(f"Exact dataset match: **{selected_job['job_title']}**")
            else:
                st.info(
                    f"Closest relevant dataset match: **{selected_job['job_title']}** "
                    f"(title relevance: {title_score * 100:.1f}%)"
                )

            job_skills = parse_list(selected_job["job_skill_set"])
            skill_vocab = set()
            for skills in catalog["skills_list"]:
                skill_vocab.update(skills)

            resume_skills = extract_resume_skills(resume_text, skill_vocab)
            matched = calculate_matches(resume_skills, job_skills)
            missing = calculate_gap(resume_skills, job_skills)
            overlap_ratio = len(matched) / len(job_skills) if job_skills else 0.0

            ml_artifacts = load_model()
            if ml_artifacts is None:
                st.error("ML model file not found. Run the ML training cells in the project notebook first.")
                st.stop()

            vectorizer = ml_artifacts["vectorizer"]
            model = ml_artifacts["model"]

            resume_tfidf = vectorizer.transform([resume_text])
            job_description_clean = clean_job_description(selected_job["job_description"])
            job_tfidf = vectorizer.transform([job_description_clean])
            tfidf_sim = float(cosine_similarity(resume_tfidf, job_tfidf)[0, 0])

            resume_emb = sentence_model.encode([resume_text], normalize_embeddings=True)
            job_emb = sentence_model.encode([job_description_clean], normalize_embeddings=True)
            semantic_sim = float(np.dot(resume_emb[0], job_emb[0]))
            semantic_sim = float(np.clip((semantic_sim + 1) / 2, 0, 1))

            features = np.array([[
                len(resume_skills),
                len(job_skills),
                overlap_ratio,
                tfidf_sim,
                semantic_sim,
            ]])
            compatibility = float(np.clip(model.predict(features)[0], 0, 100))

            headcount_rows, headcount_metadata = load_headcount_demand()
            recent_counts = recent_skill_counts(headcount_rows)
            priority_df = priority_from_demand(missing, catalog, recent_counts)

            dependencies = {
                "numpy": ["python"],
                "pandas": ["python", "numpy"],
                "matplotlib": ["python"],
                "seaborn": ["python", "pandas", "matplotlib"],
                "statistics": ["python"],
                "machine learning": ["python", "numpy", "pandas", "statistics"],
                "scikit learn": ["python", "numpy", "pandas", "machine learning"],
                "deep learning": ["python", "numpy", "machine learning"],
                "tensorflow": ["python", "numpy", "deep learning"],
                "pytorch": ["python", "numpy", "deep learning"],
                "keras": ["python", "deep learning", "tensorflow"],
                "natural language processing": ["python", "machine learning"],
                "computer vision": ["python", "numpy", "deep learning"],
                "sql": ["database"],
                "mysql": ["sql", "database"],
                "mongodb": ["database"],
                "data analysis": ["python", "pandas", "statistics"],
                "data science": ["python", "statistics", "data analysis", "machine learning"],
                "power bi": ["data analysis"],
                "tableau": ["data analysis"],
                "docker": ["linux", "software development"],
                "aws": ["cloud computing"],
                "git": ["software development"],
                "github": ["git"],
                "rest apis": ["python", "software development"],
                "flask": ["python", "rest apis"],
                "django": ["python", "software development"],
                "java": ["programming"],
                "c++": ["programming"],
                "javascript": ["programming"],
                "html": ["web development"],
                "css": ["html", "web development"],
                "react": ["javascript", "html", "css"],
                "spring": ["java", "software development"],
            }
            resources = load_resources()
            resource_records = resources.fillna("").to_dict(orient="records")
            recommendations = build_skill_recommendations(
                priority_df.fillna(0).to_dict(orient="records"),
                resource_records,
                normalize_skill,
            )
            ranked_missing = [item["Skill"] for item in recommendations] or missing
            roadmap = build_learning_roadmap(
                ranked_missing, dependencies, resume_skills, normalize_skill
            )
            learning_plan = build_learning_plan(roadmap, normalize_skill)

            st.markdown('<div class="analysis-kicker">Your results</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="analysis-title">Your match for {html.escape(str(selected_job["job_title"]))}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="match-callout"><strong>A starting point for your next move.</strong> '
                'Use this estimate alongside your experience and goals; it is not a hiring decision.</div>',
                unsafe_allow_html=True,
            )
            c1, c2, c3 = st.columns(3, gap="medium")
            c1.metric("Compatibility estimate", f"{compatibility:.1f}%")
            c2.metric("Skills matched", f"{len(matched)} of {len(job_skills)}")
            c3.metric("Skills to build", len(missing))
            st.progress(compatibility / 100, text="Prototype estimate · not a hiring probability")

            match_col, gap_col = st.columns(2, gap="large")
            with match_col:
                st.markdown('<div class="section-title">Your strengths</div>', unsafe_allow_html=True)
                render_skill_chips(matched, "match")
            with gap_col:
                st.markdown('<div class="section-title">Growth opportunities</div>', unsafe_allow_html=True)
                render_skill_chips(missing, "gap")

            with st.expander(f"About this {selected_job['job_title']} role"):
                st.caption(clean_job_description(selected_job["job_description"]))

            if not priority_df.empty:
                st.subheader("Prioritized Skill Gap")
                if headcount_metadata:
                    st.caption(
                        f"India listing window from {headcount_metadata['window_start_utc']} UTC; "
                        f"{headcount_metadata['api_records']} API records, {headcount_metadata['processed_jobs']} usable descriptions. "
                        f"Generated {headcount_metadata['generated_at_utc']} UTC. Catalog demand still determines priority."
                        + (" No listings matched this window." if int(headcount_metadata.get("api_records", "0")) == 0 else (f" No known catalog skills matched among {headcount_metadata['processed_jobs']} usable listings." if not headcount_rows else ""))
                    )
                elif recent_counts is None:
                    st.caption("Daily India listing data is not available yet; priorities use the existing catalog.")
                st.caption("Job Demand counts skill occurrences in the loaded job catalog; Demand Score is that count divided by the most frequent catalog skill. These are catalog-frequency measures, not unique vacancies or hiring probabilities. Repeated/template rows can affect the counts.")
                st.dataframe(priority_df, use_container_width=True, hide_index=True)

            st.subheader("Personalized Learning Plan")
            st.caption("Prerequisites come first. Missing skills are ranked using catalog frequency, with recent India listing counts as a modest supplementary signal. The 30/60/90-day groups are suggested pacing, not fixed course durations.")
            if roadmap:
                for phase in learning_plan:
                    with st.container(border=True):
                        st.markdown(f"**{phase['Phase']}**")
                        if phase["Skills"]:
                            st.markdown("  ·  ".join(skill.title() for skill in phase["Skills"]))
                        else:
                            st.caption("Consolidate earlier skills and practice with a small project.")
            else:
                st.write("No additional learning steps are required from the detected job skills.")

            if roadmap:
                st.subheader("Learning Progress")
                st.caption(
                    "Progress is saved in a local JSON file. Use a nickname, not sensitive information; "
                    "the profile label is hashed before storage and is not an access control."
                )
                progress_profile = st.text_input(
                    "Progress profile", value="default", key="learning_progress_profile"
                )
                completed_before_save = []
                try:
                    completed_before_save = load_progress(
                        LEARNING_PROGRESS_FILE, progress_profile, selected_job["job_title"],
                        roadmap, normalize_skill,
                    )
                except ProgressStoreError as exc:
                    st.error(str(exc))

                plan_widget_id = hashlib.sha256(
                    (selected_job["job_title"] + "\0" + "\0".join(
                        normalize_skill(skill) for skill in roadmap
                    )).encode("utf-8")
                ).hexdigest()[:12]
                profile_widget_id = hashlib.sha256(
                    " ".join(progress_profile.split()).casefold().encode("utf-8")
                ).hexdigest()[:12]
                progress_widget_keys = []
                with st.form("learning_progress_form"):
                    st.write("Mark the learning steps you have completed.")
                    for skill in roadmap:
                        widget_key = (
                            f"learning_done_{profile_widget_id}_{plan_widget_id}_"
                            f"{hashlib.sha256(normalize_skill(skill).encode('utf-8')).hexdigest()[:8]}"
                        )
                        progress_widget_keys.append((skill, widget_key))
                        st.checkbox(
                            skill.title(), value=skill in completed_before_save, key=widget_key
                        )
                    progress_submitted = st.form_submit_button("Save progress")

                selected_completed = [
                    skill for skill, widget_key in progress_widget_keys
                    if st.session_state.get(widget_key, skill in completed_before_save)
                ]
                if progress_submitted:
                    try:
                        save_progress(
                            LEARNING_PROGRESS_FILE, progress_profile, selected_job["job_title"],
                            roadmap, selected_completed, normalize_skill,
                        )
                        st.success("Learning progress saved.")
                    except ProgressStoreError as exc:
                        st.error(str(exc))
                progress_count = len(selected_completed)
                progress_ratio = progress_count / len(roadmap)
                st.progress(progress_ratio, text=f"{progress_count} of {len(roadmap)} steps completed")
                st.caption("Progress is stored at the configured local file path.")

            st.subheader("Ranked Recommendations and Resources")
            if recommendations:
                for recommendation in recommendations:
                    st.markdown(f"**{recommendation['Rank']}. {recommendation['Skill'].title()}** — {recommendation['Explanation']}")
                    if recommendation["Resources"]:
                        for resource in recommendation["Resources"]:
                            st.markdown(f"[{resource['resource']}]({resource['url']}) · {resource['type']}")
                    else:
                        st.caption("No resource is mapped for this skill in the existing catalog.")
            elif roadmap:
                st.info("No missing job skills need a recommendation.")
            if not resources.empty and roadmap:
                # Show catalog entries for prerequisite steps too, where available.
                normalized_resources = resources.copy()
                normalized_resources["skill_normalized"] = normalized_resources["skill"].map(normalize_skill)
                selected_resources = normalized_resources[
                    normalized_resources["skill_normalized"].isin({normalize_skill(x) for x in roadmap})
                ][["skill", "resource", "type", "url"]].drop_duplicates()
                if selected_resources.empty:
                    st.info("No resource link is currently mapped for the detected roadmap skills.")
                else:
                    with st.expander("All catalog resources for roadmap skills"):
                        st.dataframe(
                            selected_resources,
                            use_container_width=True,
                            hide_index=True,
                            column_config={"url": st.column_config.LinkColumn("Resource Link")},
                        )
            else:
                st.info("No learning-resource dataset is available yet.")

            with st.expander("Model Features"):
                st.write({
                    "resume_skill_count": len(resume_skills),
                    "job_skill_count": len(job_skills),
                    "skill_overlap_ratio": round(overlap_ratio, 4),
                    "tfidf_similarity": round(tfidf_sim, 4),
                    "semantic_similarity": round(semantic_sim, 4),
                })

        except Exception as exc:
            st.exception(exc)
