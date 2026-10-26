"""Shared application shell and the dashboard landing page."""

import html

import streamlit as st


PAGES = ("Dashboard", "Analyze resume")


def _open_resume_analysis():
    st.session_state["app_page"] = "Analyze resume"


def apply_app_styles():
    st.markdown(
        """
        <style>
        :root { --ink: #10182d; --muted: #69758e; --blue: #5574f7; --violet: #895cf6; }
        [data-testid="stAppViewContainer"] { background: #f6f8fc; }
        [data-testid="stHeader"] { background: rgba(246,248,252,.92); }
        [data-testid="stSidebar"] { background: #111a31; border-right: 1px solid #202b45; }
        [data-testid="stSidebar"] > div:first-child { padding-top: 1.35rem; }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #9eabc7; }
        [data-testid="stSidebar"] [data-testid="stRadio"] label { color: #dce4f8; }
        [data-testid="stSidebar"] [data-testid="stRadio"] label p { color: #dce4f8; }
        .brand-row { display:flex; align-items:center; gap:12px; margin: 2px 0 30px; }
        .brand-mark { width:38px; height:38px; border-radius:12px; display:grid; place-items:center;
          color:#fff; font-weight:800; background:linear-gradient(135deg,#5b7bff,#9562f5);
          box-shadow:0 8px 22px rgba(89,111,242,.3); }
        .brand-name { color:#f6f8ff; font-size:15px; font-weight:750; letter-spacing:-.2px; }
        .brand-caption { color:#8997b7; font-size:11px; margin-top:2px; }
        .side-section { color:#71809f; text-transform:uppercase; letter-spacing:1.2px;
          font-size:10px; font-weight:750; margin: 0 0 8px; }
        .side-footer { border-top:1px solid #2a3550; margin-top:28px; padding-top:16px;
          color:#95a2bd; font-size:12px; line-height:1.55; }
        .eyebrow { color:#6578c9; text-transform:uppercase; letter-spacing:1.6px;
          font-size:11px; font-weight:800; margin-bottom:10px; }
        .dashboard-title { color:var(--ink); font-size:clamp(30px,4vw,43px); line-height:1.12;
          letter-spacing:-1.7px; font-weight:780; max-width:720px; margin:0 0 12px; }
        .dashboard-copy { color:var(--muted); font-size:16px; line-height:1.65; max-width:640px; }
        .hero-panel { position:relative; overflow:hidden; border-radius:24px; padding:36px 38px;
          background:linear-gradient(118deg,#111a31 0%,#1c2a50 58%,#463a88 100%);
          color:#fff; box-shadow:0 18px 48px rgba(34,49,91,.15); }
        .hero-panel:after { content:""; position:absolute; width:260px; height:260px; right:6%; top:-120px;
          border-radius:50%; border:1px solid rgba(255,255,255,.12);
          box-shadow:0 0 0 28px rgba(255,255,255,.035),0 0 0 62px rgba(255,255,255,.025); }
        .hero-kicker { color:#c7d2ff; font-size:12px; font-weight:700; letter-spacing:1.2px;
          text-transform:uppercase; margin-bottom:12px; }
        .hero-title { color:#fff; font-size:clamp(25px,3vw,34px); line-height:1.2;
          font-weight:760; letter-spacing:-.8px; max-width:570px; margin:0 0 10px; }
        .hero-copy { color:#c1cbe1; line-height:1.6; max-width:560px; font-size:14px; margin-bottom:22px; }
        .section-title { color:var(--ink); font-size:19px; font-weight:750; letter-spacing:-.35px; }
        .step-card { background:#fff; border:1px solid #e9edf5; border-radius:17px; padding:20px;
          min-height:155px; box-shadow:0 5px 18px rgba(25,42,82,.035); }
        .step-number { color:#687bf0; font-size:11px; font-weight:800; letter-spacing:1.2px; }
        .step-heading { color:#162039; font-size:15px; font-weight:750; margin:9px 0 6px; }
        .step-copy { color:#71809a; font-size:13px; line-height:1.5; }
[data-testid="stTextInput"] input, [data-testid="stSelectbox"] [role="combobox"] { border-radius:10px; }
[data-testid="stDataFrame"] { border:1px solid #e9edf5; border-radius:12px; overflow:hidden; }
        .analysis-kicker { color:#6578c9; text-transform:uppercase; letter-spacing:1.5px;
          font-size:11px; font-weight:800; margin-bottom:8px; }
        .analysis-title { color:#10182d; font-size:clamp(30px,4vw,42px); line-height:1.12;
          letter-spacing:-1.5px; font-weight:780; margin:0 0 10px; }
        .analysis-copy { color:#69758e; font-size:15px; line-height:1.65; max-width:700px; }
        .analysis-step { display:flex; align-items:center; gap:10px; color:#68758e;
          font-size:12px; font-weight:650; padding:7px 0 13px; }
        .analysis-step span { width:25px; height:25px; border-radius:50%; display:grid; place-items:center;
          background:#edf0ff; color:#536de8; font-size:11px; font-weight:800; }
        [data-testid="stFileUploaderDropzone"] { border:1.5px dashed #b9c5e5; border-radius:14px;
          background:#f8faff; }
        [data-testid="stMetric"] { background:#fff; border:1px solid #e7ebf4; border-radius:15px;
          padding:15px 17px; box-shadow:0 5px 18px rgba(25,42,82,.035); }
        [data-testid="stMetricLabel"] { color:#69758e; font-weight:650; }
        .skill-list { display:flex; flex-wrap:wrap; gap:8px; margin:10px 0 15px; }
        .skill-chip { display:inline-flex; align-items:center; border-radius:999px; padding:7px 11px;
          font-size:12px; line-height:1.2; font-weight:700; border:1px solid transparent; }
        .skill-chip.match { color:#14734d; background:#e8f7ef; border-color:#caecd9; }
        .skill-chip.gap { color:#9b4b25; background:#fff2e8; border-color:#f5d7c3; }
        .match-callout { border-radius:16px; padding:18px 20px; margin:12px 0 18px;
          background:linear-gradient(110deg,#eff3ff,#f8f5ff); border:1px solid #e1e7ff; }
        .match-callout strong { color:#243b88; }
        .score-card { display:flex; align-items:center; gap:20px; min-height:160px; padding:18px 20px;
          background:linear-gradient(125deg,#111a31,#26376d 72%,#4a438c); border-radius:18px;
          box-shadow:0 12px 30px rgba(34,49,91,.13); color:#fff; }
        .score-ring { width:126px; height:126px; flex:0 0 126px; border-radius:50%; display:flex;
          align-items:center; justify-content:center; position:relative;
          background:conic-gradient(#9db0ff var(--score),rgba(255,255,255,.16) 0); }
        .score-ring:before { content:""; position:absolute; inset:10px; border-radius:50%; background:#18264a; }
        .score-ring-copy { position:relative; z-index:1; display:flex; flex-direction:column; align-items:center; }
        .score-ring-value { color:#fff; font-size:27px; line-height:1.05; font-weight:780; letter-spacing:-.7px; }
        .score-ring-label { color:#cbd5f1; font-size:10px; font-weight:650; margin-top:5px; }
        .score-title { color:#fff; font-size:16px; font-weight:750; margin-bottom:6px; }
        .score-description { color:#cbd5e8; font-size:12px; line-height:1.55; max-width:280px; }
        [data-testid="stMainBlockContainer"] { padding-top:2rem; padding-bottom:3rem; }
        @media (max-width:700px) {
          [data-testid="stMainBlockContainer"] { padding-top:1.2rem; }
          .hero-panel { padding:26px 22px; border-radius:19px; }
          .score-card { flex-direction:column; align-items:flex-start; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar():
    with st.sidebar:
        st.markdown(
            '<div class="brand-row"><div class="brand-mark">S</div><div>'
            '<div class="brand-name">SkillScope</div><div class="brand-caption">Career intelligence</div>'
            '</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="side-section">Workspace</div>', unsafe_allow_html=True)
        page = st.radio(
            "Workspace navigation",
            PAGES,
            label_visibility="collapsed",
            key="app_page",
        )
        st.markdown(
            '<div class="side-footer"><strong style="color:#e5ebfa">Your next step, made clearer.</strong>'
            '<br/>Understand your strengths and build toward the role you want.</div>',
            unsafe_allow_html=True,
        )
    return page



def render_skill_chips(skills, tone="match"):
    """Render safely escaped skill labels in compact, accessible chips."""
    if not skills:
        st.caption("No direct skill matches detected." if tone == "match" else "No missing skills detected.")
        return
    chips = "".join(
        f'<span class="skill-chip {tone}">{html.escape(str(skill))}</span>'
        for skill in skills
    )
    st.markdown(f'<div class="skill-list">{chips}</div>', unsafe_allow_html=True)

def render_dashboard(demand_rows=None, demand_metadata=None, progress_summary=None, progress_error=None, snapshot_status=None, recent_demand_rows=None, role_rows=None, recent_title_rows=None, title_metadata=None, title_status=None):
    st.markdown('<div class="eyebrow">Career growth workspace</div>', unsafe_allow_html=True)
    st.markdown('<div class="dashboard-title">Turn your skills into your next opportunity.</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="dashboard-copy">Get a clearer view of how your experience aligns with a role, '
        'then focus your learning on the skills that matter.</div>',
        unsafe_allow_html=True,
    )
    st.write("")
    st.markdown(
        '<div class="hero-panel"><div class="hero-kicker">A smarter starting point</div>'
        '<div class="hero-title">Make your next career move with confidence.</div>'
        '<div class="hero-copy">Bring your resume and a role you have in mind. SkillScope will help '
        'you understand your match and shape a practical path forward.</div></div>',
        unsafe_allow_html=True,
    )
    st.write("")
    st.button(
        "Start with your resume  →",
        type="primary",
        key="dashboard_start",
        on_click=_open_resume_analysis,
    )
    if st.button("Reload dashboard data", key="dashboard_refresh"):
        st.cache_data.clear()
        st.rerun()
    st.caption("Reload reads the catalog and latest bundled snapshot from disk. It does not start a new listings import.")

    st.write("")
    st.markdown('<div class="section-title">Explore job titles</div>', unsafe_allow_html=True)
    st.caption("Search unique titles represented by actual rows in the bundled job catalog. Catalog rows may be repeated templates; they are not live vacancies.")
    if role_rows:
        roles = role_rows.copy()
        family_values = sorted({category for role in roles for category in role["Categories"].split(", ") if category})
        search_col, family_col = st.columns([1.4, 1], gap="medium")
        with search_col:
            title_query = st.text_input("Search job titles", placeholder="Try ‘backend’, ‘data’, or ‘cloud’", key="role_search")
        with family_col:
            selected_family = st.selectbox("Catalog category", ["All categories", *family_values], key="role_category")
        query = title_query.strip().casefold()
        filtered = [role for role in roles if query in role["Job title"].casefold()
                    and (selected_family == "All categories" or selected_family in role["Categories"].split(", "))]
        st.metric("Distinct catalog titles", len(roles))
        if filtered:
            st.dataframe(filtered, use_container_width=True, hide_index=True)
        else:
            st.info("No catalog titles match those filters. Try another search or select all categories.")
        st.caption("The bundled catalog has no per-title source timestamps. Its title list is a static dataset snapshot, not a current market inventory.")
    else:
        st.info("Job-title discovery is unavailable because the bundled catalog could not be loaded.")
    st.markdown("**Recently observed provider titles**")
    if title_metadata is None or title_status is None or title_status["state"] == "unavailable":
        st.info("The bundled provider snapshot does not contain a validated title aggregate yet. Titles will appear here after a successful provider refresh.")
    else:
        if title_status["state"] == "stale":
            st.warning(title_status["message"])
        if title_status["state"] == "no_listings":
            st.info("The latest provider run found no records in its 48-hour posting window.")
        elif recent_title_rows:
            st.dataframe(recent_title_rows, use_container_width=True, hide_index=True)
            st.caption(
                f"{len(recent_title_rows)} distinct titles from the limited India posting sample, generated "
                f"{title_metadata.get('generated_at_utc', 'at an unknown time')} UTC. Counts are distinct provider records; "
                "title-only aggregates do not provide the skill details needed for resume analysis."
            )
        else:
            st.info("The provider checked recent records but none had a usable job title.")

    st.write("")
    st.markdown('<div class="section-title">A clear path from experience to action</div>', unsafe_allow_html=True)
    st.caption("Three focused steps to help you move forward.")
    columns = st.columns(3, gap="medium")
    cards = (
        ("01", "Share your experience", "Upload a resume and choose the role you want to explore."),
        ("02", "See your alignment", "Review your strengths and the skills that could close the gap."),
        ("03", "Build your next steps", "Use a personalized learning roadmap to keep making progress."),
    )
    for column, (number, title, copy) in zip(columns, cards):
        with column:
            st.markdown(
                f'<div class="step-card"><div class="step-number">{number} / 03</div>'
                f'<div class="step-heading">{title}</div><div class="step-copy">{copy}</div></div>',
                unsafe_allow_html=True,
            )

    st.write("")
    st.markdown('<div class="section-title">Your skills and learning activity</div>', unsafe_allow_html=True)
    demand_column, progress_column = st.columns([1.15, 0.85], gap="large")
    with demand_column:
        st.subheader("Skills appearing in the job catalog")
        if demand_rows:
            st.dataframe(demand_rows, use_container_width=True, hide_index=True)
            st.markdown("**Most mentioned catalog skills**")
            st.bar_chart({row["Skill"]: row["Catalog mentions"] for row in demand_rows}, horizontal=True)
            st.caption(
                "Counts are skill mentions in the included catalog. Repeated or template rows can affect them; "
                "they are not counts of distinct vacancies or hiring probabilities."
            )
            if demand_metadata:
                st.caption(
                    "Recent India listings are a separate, limited 48-hour posting-window snapshot, generated "
                    f"{demand_metadata.get('generated_at_utc', 'at an unknown time')} UTC."
                )
                if snapshot_status:
                    if snapshot_status["state"] in {"no_listings", "no_skill_matches", "unavailable"}:
                        st.info(snapshot_status["message"])
                    elif snapshot_status["state"] == "stale":
                        st.warning(snapshot_status["message"])
                    else:
                        st.caption(snapshot_status["message"])
                if recent_demand_rows:
                    st.markdown("**Skills observed in the latest India snapshot**")
                    st.bar_chart({row["Skill"]: row["Recent India listings"] for row in recent_demand_rows}, horizontal=True)
                elif snapshot_status and snapshot_status["state"] == "available":
                    st.info("No catalog skill was observed in the latest listing sample.")
            elif snapshot_status:
                st.info(snapshot_status["message"])
        else:
            st.info("Skill-demand summaries are unavailable because the job catalog could not be loaded or was malformed.")

    with progress_column:
        st.subheader("Saved learning progress")
        if progress_error:
            st.warning(f"Saved progress could not be read: {progress_error}")
        elif progress_summary:
            st.metric("Saved learning plans", progress_summary["saved_plan_count"])
            st.metric("Completed step records", progress_summary["completed_step_count"])
            if progress_summary.get("tracked_plan_count", 0):
                st.metric("Plans completed", f"{progress_summary['fully_completed_plan_count']} / {progress_summary['tracked_plan_count']}")
                st.progress(
                    progress_summary["completion_ratio"],
                    text=f"{progress_summary['completed_tracked_step_count']} of {progress_summary['tracked_step_count']} steps completed across plans with saved totals",
                )
                if progress_summary.get("untracked_plan_count", 0):
                    st.caption(f"{progress_summary['untracked_plan_count']} older plan(s) do not have a saved step total yet; totals are added the next time progress is saved.")
            if progress_summary["last_updated"]:
                st.caption(f"Last saved: {progress_summary['last_updated']} UTC")
            elif progress_summary["saved_plan_count"] == 0:
                st.caption("No learning plans have been saved yet. Analyze a resume, then save progress from its learning plan to build this summary.")
            st.caption("Totals cover saved local profiles; a step saved in two plans is counted twice.")
        else:
            st.info("Saved learning progress is unavailable.")
        st.button(
            "Open resume analysis  →",
            key="dashboard_progress_action",
            on_click=_open_resume_analysis,
        )
