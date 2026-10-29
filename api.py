"""FastAPI adapter for the existing SkillScope model and file-backed data."""
from __future__ import annotations

import ast
import difflib
import html
import io
import os
import re
from pathlib import Path
from typing import Annotated

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sklearn.metrics.pairwise import cosine_similarity

from app_helpers import (build_learning_plan, build_learning_roadmap,
                         build_skill_recommendations, summarize_recent_snapshot)
from data_pipeline.skill_demand import (load_headcount_demand as read_headcount_demand,
                                        load_headcount_titles as read_headcount_titles,
                                        recent_skill_counts)
from learning_progress import (ProgressStoreError, load_progress, save_progress,
                               summarize_progress)
from role_discovery import catalog_roles

ROOT = Path(__file__).resolve().parent
MODEL_FILE = ROOT / "resume_job_ml_model.pkl"
JOB_FILE = Path(os.environ.get("SKILLSCOPE_JOB_CATALOG", ROOT / "job_catalog.csv"))
RESOURCE_FILE = ROOT / "learning_resources.csv"
DEMAND_FILE = Path(os.environ.get("SKILLSCOPE_DEMAND_CSV", ROOT / "data_pipeline/headcount_skill_demand.csv"))
DEMAND_META = Path(os.environ.get("SKILLSCOPE_DEMAND_METADATA", ROOT / "data_pipeline/headcount_skill_demand.metadata.json"))
TITLES_FILE = Path(os.environ.get("SKILLSCOPE_TITLES_CSV", ROOT / "data_pipeline/headcount_job_titles.csv"))
PROGRESS_FILE = Path(os.environ.get("LEARNING_PROGRESS_FILE", ROOT / "data/learning_progress.json"))

app = FastAPI(title="SkillScope API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("SKILLSCOPE_CORS_ORIGINS", "http://localhost:5173").split(","), allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["*"])
_model = None
_encoder = None
_title_cache = None
_title_cache_names = ()


def normalize_skill(skill):
    value = " ".join(str(skill).lower().strip().replace(".", "").replace("-", " ").split())
    aliases = {"scikit learn": "scikit learn", "auto cad": "autocad", "autocad": "autocad", "tensorflow keras": "tensorflow", "mysql database": "mysql", "r or java": "r or java"}
    return aliases.get(value, value)


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
    except (ValueError, SyntaxError):
        pass
    return [x.strip() for x in re.split(r"[,;|]", text) if x.strip()]


def clean_text(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", str(value or "")))).strip()


def catalog():
    if not JOB_FILE.exists():
        raise HTTPException(503, "The bundled job catalog is unavailable.")
    frame = pd.read_csv(JOB_FILE)
    required = {"job_title", "category", "job_description", "job_skill_set"}
    if not required.issubset(frame.columns):
        raise HTTPException(503, "The bundled job catalog is missing required columns.")
    frame["job_description"] = frame["job_description"].fillna("").map(clean_text)
    frame["skills_list"] = frame["job_skill_set"].apply(parse_list)
    return frame


def resources():
    return pd.read_csv(RESOURCE_FILE).fillna("").to_dict(orient="records") if RESOURCE_FILE.exists() else []


def get_model():
    global _model
    if _model is None:
        if not MODEL_FILE.exists():
            raise HTTPException(503, "The saved compatibility model is unavailable.")
        _model = joblib.load(MODEL_FILE)
    return _model


def get_encoder():
    global _encoder
    if _encoder is None:
        try:
            from sentence_transformers import SentenceTransformer
            _encoder = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as exc:
            raise HTTPException(503, "The sentence model could not be loaded. Check network access or model cache.") from exc
    return _encoder


def extract_resume(text, vocabulary):
    normalized = " ".join(re.sub(r"[^a-z0-9+#.\-/ ]", " ", text.lower()).split())
    found = []
    for skill in sorted(vocabulary, key=len, reverse=True):
        key = normalize_skill(skill)
        if key and re.search(r"(?<![a-z0-9])" + re.escape(key) + r"(?![a-z0-9])", normalized):
            found.append(skill)
    aliases = {"scikit learn": ["scikit-learn", "scikit learn", "sklearn"], "c++": ["c++"], "c#": ["c#", "c sharp"], "javascript": ["javascript", "java script"], "machine learning": ["machine learning", "ml"], "deep learning": ["deep learning", "dl"]}
    for canonical, variants in aliases.items():
        if any(re.search(r"(?<![a-z0-9])" + re.escape(v) + r"(?![a-z0-9])", text.lower()) for v in variants):
            found.append(canonical)
    return list(dict.fromkeys(found))


def normalize_title(title):
    value = " ".join(re.sub(r"[^a-z0-9+# ]", " ", str(title).lower().strip()).split())
    return {"ml engineer": "machine learning engineer", "ml developer": "machine learning developer", "ai engineer": "artificial intelligence engineer", "software developer": "software engineer", "application developer": "software developer"}.get(value, value)


def title_tokens(title):
    generic = {"engineer", "developer", "developers", "senior", "junior", "sr", "jr", "lead", "principal", "associate", "specialist", "consultant", "manager", "architect", "professional", "intern", "trainee", "ii", "iii"}
    return set(normalize_title(title).split()) - generic


def choose_job(query, frame, encoder):
    global _title_cache, _title_cache_names
    norm = normalize_title(query)
    normalized = frame.job_title.map(normalize_title)
    exact = frame[normalized == norm]
    if not exact.empty:
        return exact.iloc[0], 1.0, "exact"
    q_tokens = title_tokens(query)
    if not q_tokens:
        return None, 0.0, "none"
    ranked = []
    for idx, title in frame.job_title.items():
        tokens = title_tokens(title)
        overlap = q_tokens & tokens
        recall = len(overlap) / len(q_tokens)
        precision = len(overlap) / len(tokens) if tokens else 0
        f1 = 2 * recall * precision / (recall + precision) if recall + precision else 0
        if recall >= 1:
            ranked.append((idx, title, f1))
    if ranked:
        if len(ranked) > 1:
            q = encoder.encode([query], normalize_embeddings=True, show_progress_bar=False)[0]
            candidates = encoder.encode([r[1] for r in ranked], normalize_embeddings=True, show_progress_bar=False)
            scores = np.dot(candidates, q)
            best_i = max(range(len(ranked)), key=lambda i: (scores[i], ranked[i][2]))
            row = frame.loc[ranked[best_i][0]]
            return row, float(np.clip((scores[best_i] + 1) / 2, 0, 1)), "strong-token"
        idx, _, _ = max(ranked, key=lambda r: r[2])
        return frame.loc[idx], 0.85, "strong-token"
    titles = frame.job_title.astype(str).tolist()
    if _title_cache is None or _title_cache_names != tuple(titles):
        _title_cache = encoder.encode(titles, normalize_embeddings=True, show_progress_bar=False)
        _title_cache_names = tuple(titles)
    title_embeddings = _title_cache
    query_embedding = encoder.encode([query], normalize_embeddings=True, show_progress_bar=False)[0]
    semantic_scores = np.dot(title_embeddings, query_embedding)
    best_idx = int(np.argmax(semantic_scores))
    best_score = float(np.clip((semantic_scores[best_idx] + 1) / 2, 0, 1))
    best_tokens = title_tokens(titles[best_idx])
    recall = len(q_tokens & best_tokens) / len(q_tokens)
    if best_score >= .72 and recall >= .5:
        return frame.iloc[best_idx], best_score, "semantic"
    for title in difflib.get_close_matches(query, titles, n=5, cutoff=.70):
        if len(q_tokens & title_tokens(title)) / len(q_tokens) >= .5:
            return frame[frame.job_title == title].iloc[0], .70, "fuzzy"
    return None, 0.0, "none"


def matches(resume_skills, job_skills):
    found, missing, seen = [], [], set()
    for skill in job_skills:
        key = normalize_skill(skill)
        if key in seen:
            continue
        seen.add(key)
        if any(normalize_skill(user) == key or key == "r or java" and normalize_skill(user) in {"r", "java"} for user in resume_skills):
            found.append(skill)
        else:
            missing.append(skill)
    return found, missing


DEPENDENCIES = {"numpy": ["python"], "pandas": ["python", "numpy"], "matplotlib": ["python"], "seaborn": ["python", "pandas", "matplotlib"], "statistics": ["python"], "machine learning": ["python", "numpy", "pandas", "statistics"], "scikit learn": ["python", "numpy", "pandas", "machine learning"], "deep learning": ["python", "numpy", "machine learning"], "tensorflow": ["python", "numpy", "deep learning"], "pytorch": ["python", "numpy", "deep learning"], "keras": ["python", "deep learning", "tensorflow"], "natural language processing": ["python", "machine learning"], "computer vision": ["python", "numpy", "deep learning"], "sql": ["database"], "mysql": ["sql", "database"], "mongodb": ["database"], "data analysis": ["python", "pandas", "statistics"], "data science": ["python", "statistics", "data analysis", "machine learning"], "power bi": ["data analysis"], "tableau": ["data analysis"], "docker": ["linux", "software development"], "aws": ["cloud computing"], "git": ["software development"], "github": ["git"], "rest apis": ["python", "software development"], "flask": ["python", "rest apis"], "django": ["python", "software development"], "java": ["programming"], "c++": ["programming"], "javascript": ["programming"], "html": ["web development"], "css": ["html", "web development"], "react": ["javascript", "html", "css"], "spring": ["java", "software development"]}


class ProgressUpdate(BaseModel):
    profile: str = Field(min_length=1, max_length=80)
    job_title: str
    roadmap: list[str]
    completed_skills: list[str]


@app.get("/api/health")
def health():
    return {"status": "ok", "model_available": MODEL_FILE.exists(), "catalog_available": JOB_FILE.exists()}


@app.get("/api/dashboard")
def dashboard():
    frame = catalog()
    roles = catalog_roles(frame)
    counts = {}
    labels = {}
    for skills in frame.skills_list:
        for skill in skills:
            key = normalize_skill(skill)
            counts[key] = counts.get(key, 0) + 1
            labels.setdefault(key, skill)
    demand = [{"skill": labels[k], "catalog_mentions": v} for k, v in sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:10]]
    rows, metadata = read_headcount_demand(DEMAND_FILE, normalize_skill, DEMAND_META)
    recent = recent_skill_counts(rows)
    try:
        progress = summarize_progress(PROGRESS_FILE)
    except ProgressStoreError as exc:
        progress = None
        progress_error = str(exc)
    else:
        progress_error = None
    titles, title_meta = read_headcount_titles(TITLES_FILE, DEMAND_META)
    return {"roles": roles, "categories": sorted({c for role in roles for c in role["Categories"].split(", ") if c}), "catalog_skill_demand": demand, "recent_skill_counts": recent, "recent_snapshot": {"metadata": metadata, "status": summarize_recent_snapshot(rows, metadata)}, "recent_titles": titles, "recent_title_metadata": title_meta, "progress": progress, "progress_error": progress_error}


@app.post("/api/analyze")
async def analyze(resume: Annotated[UploadFile, File()], job_title: Annotated[str, Form()], profile: Annotated[str, Form()] = "default"):
    suffix = Path(resume.filename or "").suffix.lower()
    data = await resume.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(413, "Resume file must be 10 MB or smaller.")
    try:
        if suffix == ".txt":
            text = data.decode("utf-8", errors="ignore")
        elif suffix == ".pdf":
            from pypdf import PdfReader
            text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)
        elif suffix == ".docx":
            from docx import Document
            text = "\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs)
        else:
            raise HTTPException(400, "Upload a PDF, DOCX, or TXT resume.")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f"Could not read this resume: {exc}") from exc
    if len(text.strip()) < 50:
        raise HTTPException(400, "Very little text was extracted. Try a text-based PDF or DOCX.")
    return analyze_text(text, job_title, profile)


def analyze_text(text: str, job_title: str, profile: str = "default"):
    frame = catalog()
    encoder = get_encoder()
    role, title_score, method = choose_job(job_title, frame, encoder)
    if role is None:
        raise HTTPException(422, "No sufficiently relevant catalog job title was found. Try a more specific title from Explore jobs.")
    job_skills = role.skills_list
    vocabulary = {skill for skills in frame.skills_list for skill in skills}
    user_skills = extract_resume(text, vocabulary)
    matched, missing = matches(user_skills, job_skills)
    overlap = len(matched) / len(job_skills) if job_skills else 0
    artifacts = get_model()
    encoder = get_encoder()
    clean_description = clean_text(role.job_description)
    keyword = float(cosine_similarity(artifacts["vectorizer"].transform([text]), artifacts["vectorizer"].transform([clean_description]))[0, 0])
    embeddings = encoder.encode([text, clean_description], normalize_embeddings=True)
    semantic = float(np.clip((float(np.dot(embeddings[0], embeddings[1])) + 1) / 2, 0, 1))
    features = np.array([[len(user_skills), len(job_skills), overlap, keyword, semantic]])
    score = float(np.clip(artifacts["model"].predict(features)[0], 0, 100))
    demand_rows, metadata = read_headcount_demand(DEMAND_FILE, normalize_skill, DEMAND_META)
    recent = recent_skill_counts(demand_rows)
    freq = {}
    for skills in frame.skills_list:
        for skill in skills:
            key = normalize_skill(skill)
            freq[key] = freq.get(key, 0) + 1
    max_freq = max(freq.values(), default=1)
    priority = [{"Skill": skill, "Job Demand": freq.get(normalize_skill(skill), 0), "Demand Score": round(freq.get(normalize_skill(skill), 0) / max_freq, 3), "Priority": "High" if freq.get(normalize_skill(skill), 0) / max_freq >= .5 else "Medium" if freq.get(normalize_skill(skill), 0) / max_freq >= .2 else "Low"} for skill in missing]
    priority.sort(key=lambda row: row["Demand Score"], reverse=True)
    if recent is not None:
        for row in priority:
            row["Recent India Listings (48h)"] = recent.get(normalize_skill(row["Skill"]), 0)
    recommendations = build_skill_recommendations(priority, resources(), normalize_skill)
    roadmap = build_learning_roadmap([x["Skill"] for x in recommendations] or missing, DEPENDENCIES, user_skills, normalize_skill)
    try:
        completed = load_progress(PROGRESS_FILE, profile, role.job_title, roadmap, normalize_skill)
    except ProgressStoreError:
        completed = []
    return {"role": {"title": str(role.job_title), "category": str(role.category)}, "title_match": {"method": method, "relevance": title_score}, "compatibility": round(score, 1), "signals": {"skill_coverage": overlap, "keyword_similarity": keyword, "semantic_similarity": semantic}, "resume_skills": user_skills, "matched_skills": matched, "missing_skills": missing, "priority": priority, "recommendations": recommendations, "roadmap": roadmap, "learning_plan": build_learning_plan(roadmap, normalize_skill), "completed_skills": completed, "caveat": "Prototype estimate trained on constructed labels; not a hiring probability or interview prediction.", "market_metadata": metadata}


@app.post("/api/progress")
def update_progress(update: ProgressUpdate):
    try:
        save_progress(PROGRESS_FILE, update.profile, update.job_title, update.roadmap, update.completed_skills, normalize_skill)
        completed = load_progress(PROGRESS_FILE, update.profile, update.job_title, update.roadmap, normalize_skill)
        summary = summarize_progress(PROGRESS_FILE)
    except ProgressStoreError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"completed_skills": completed, "progress": summary}

