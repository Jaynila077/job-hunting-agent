"""Streamlit dashboard for viewing and managing job hunting opportunities."""

import json
import sqlite3
from pathlib import Path
import streamlit as st
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from jobagent.config import load_settings
from jobagent.db import connect, init_db
from jobagent.decisions import get_jobs_by_status, get_status_counts, set_job_status
from jobagent.jobs import format_job_inspect, process_job
from jobagent.llm import LLMError, call_llm
from jobagent.log import setup_logging
from jobagent.profile import get_latest_profile_envelope

st.set_page_config(page_title="Job Hunting Agent", layout="wide")

settings = load_settings()
setup_logging(settings.log_level)


@st.cache_resource
def get_database_connection(db_path: str) -> sqlite3.Connection:
    conn = connect(settings.db_path)
    init_db(conn)
    return conn


conn = get_database_connection(str(settings.db_path))

st.title("Personal AI Job Hunt Agent")
st.caption(f"Profile Database: `{settings.db_path.name}` | LLM: `{settings.llm_model}`")

counts = get_status_counts(conn)

tab_new, tab_saved, tab_applied, tab_interviewing, tab_rejected, tab_add = st.tabs(
    [
        f"New ({counts['new']})",
        f"Saved ({counts['saved']})",
        f"Applied ({counts['applied']})",
        f"Interviewing ({counts['interviewing']})",
        f"Rejected ({counts['rejected']})",
        "➕ Add Job",
    ]
)


def render_job_card(job: dict, current_tab: str) -> None:
    """Renders a single job card with action buttons."""
    # Dashboard workflow focuses on scored jobs; non-scored remain viewable via inspect CLI.
    if job.get("outcome") != "scored":
        return

    title = job.get("title") or "Unknown Role"
    company = job.get("company") or "Unknown Company"
    score = job.get("score")
    verdict = (job.get("verdict") or "").upper()

    score_badge = f"**Score:** {score}/10 ({verdict})" if score else ""

    with st.container(border=True):
        col_hdr, col_score = st.columns([3, 1])
        with col_hdr:
            st.subheader(f"{title} @ {company}")
            cities = json.loads(job.get("cities_json") or "[]")
            loc_str = ", ".join(cities) if cities else (job.get("location_text") or "Not stated")
            mode = job.get("work_mode") or "unknown"
            st.write(f"**Location:** {loc_str} ({mode})")
            if job.get("url"):
                st.markdown(f"🔗 [Application Link]({job['url']})")
        with col_score:
            st.markdown(score_badge)
            exp_min = job.get("experience_min_years")
            exp_str = f"{exp_min:g}+ yrs" if exp_min is not None else "Not stated"
            st.write(f"**Experience:** {exp_str}")

        st.markdown(f"**Explanation:** {job.get('explanation') or 'N/A'}")

        matches = json.loads(job.get("matches_json") or "[]")
        gaps = json.loads(job.get("gaps_json") or "[]")

        col_m, col_g = st.columns(2)
        with col_m:
            st.markdown("**Matches:**")
            if matches:
                for m in matches:
                    st.markdown(f"- {m['requirement']} → *{m['profile_item']}*")
            else:
                st.caption("No direct matches recorded.")
        with col_g:
            st.markdown("**Gaps:**")
            if gaps:
                for g in gaps:
                    st.markdown(f"- {g}")
            else:
                st.caption("No notable gaps.")

        st.divider()

        # Decision action controls
        if current_tab == "new":
            col_save, col_app, col_int, col_rej = st.columns(4)
            with col_save:
                if st.button("Save", key=f"save_{job['id']}", use_container_width=True):
                    set_job_status(conn, job["id"], "saved")
                    st.rerun()
            with col_app:
                if st.button("Applied", key=f"app_{job['id']}", use_container_width=True):
                    set_job_status(conn, job["id"], "applied")
                    st.rerun()
            with col_int:
                if st.button("Interview", key=f"int_{job['id']}", use_container_width=True):
                    set_job_status(conn, job["id"], "interviewing")
                    st.rerun()
            with col_rej:
                with st.popover("Reject", use_container_width=True):
                    with st.form(key=f"rej_form_{job['id']}"):
                        reason = st.text_input("Rejection reason (optional):")
                        if st.form_submit_button("Confirm Rejection"):
                            set_job_status(conn, job["id"], "rejected", reason=reason or None)
                            st.rerun()

        elif current_tab == "saved":
            col_app, col_int, col_rej = st.columns(3)
            with col_app:
                if st.button("Applied", key=f"saved_app_{job['id']}", use_container_width=True):
                    set_job_status(conn, job["id"], "applied")
                    st.rerun()
            with col_int:
                if st.button(
                    "Interview", key=f"saved_int_{job['id']}", use_container_width=True
                ):
                    set_job_status(conn, job["id"], "interviewing")
                    st.rerun()
            with col_rej:
                with st.popover("Reject", use_container_width=True):
                    with st.form(key=f"saved_rej_{job['id']}"):
                        reason = st.text_input("Rejection reason (optional):")
                        if st.form_submit_button("Confirm Rejection"):
                            set_job_status(conn, job["id"], "rejected", reason=reason or None)
                            st.rerun()

        elif current_tab == "applied":
            col_int, col_rej = st.columns(2)
            with col_int:
                if st.button(
                    "🤝 Interviewing", key=f"app_int_{job['id']}", use_container_width=True
                ):
                    set_job_status(conn, job["id"], "interviewing")
                    st.rerun()
            with col_rej:
                with st.popover("Reject", use_container_width=True):
                    with st.form(key=f"app_rej_{job['id']}"):
                        reason = st.text_input("Rejection reason (optional):")
                        if st.form_submit_button("Confirm Rejection"):
                            set_job_status(conn, job["id"], "rejected", reason=reason or None)
                            st.rerun()

        elif current_tab == "interviewing":
            with st.popover("Rejection / Closed", use_container_width=True):
                with st.form(key=f"int_rej_{job['id']}"):
                    reason = st.text_input("Outcome / Reason (optional):")
                    if st.form_submit_button("Confirm"):
                        set_job_status(conn, job["id"], "rejected", reason=reason or None)
                        st.rerun()

        elif current_tab == "rejected":
            if job.get("decision_reason"):
                st.info(f"**Rejection reason:** {job['decision_reason']}")


with tab_new:
    jobs_new = get_jobs_by_status(conn, "new")
    if not jobs_new:
        st.info("No new jobs to review.")
    for j in jobs_new:
        render_job_card(j, "new")

with tab_saved:
    jobs_saved = get_jobs_by_status(conn, "saved")
    if not jobs_saved:
        st.info("No saved jobs yet.")
    for j in jobs_saved:
        render_job_card(j, "saved")

with tab_applied:
    jobs_applied = get_jobs_by_status(conn, "applied")
    if not jobs_applied:
        st.info("No applied jobs tracked.")
    for j in jobs_applied:
        render_job_card(j, "applied")

with tab_interviewing:
    jobs_interviewing = get_jobs_by_status(conn, "interviewing")
    if not jobs_interviewing:
        st.info("No active interviews.")
    for j in jobs_interviewing:
        render_job_card(j, "interviewing")

with tab_rejected:
    jobs_rejected = get_jobs_by_status(conn, "rejected")
    if not jobs_rejected:
        st.info("No rejected jobs.")
    for j in jobs_rejected:
        render_job_card(j, "rejected")

with tab_add:
    st.subheader("Add Job Posting")
    st.write("Paste a job posting below to run extraction, filtering, and fit scoring.")

    profile_envelope = get_latest_profile_envelope(settings.profile_dir)
    if profile_envelope is None:
        st.error("No profile found. Please run 'python -m jobagent profile build' first.")
    elif not settings.groq_api_key:
        st.error("GROQ_API_KEY is missing from environment or .env.")
    else:
        with st.form("manual_add_job_form", clear_on_submit=False):
            job_text = st.text_area("Job Posting Text:", height=250)
            col_u, col_s = st.columns(2)
            with col_u:
                job_url = st.text_input("Job URL (optional):")
            with col_s:
                job_source = st.text_input("Source:", value="dashboard")

            submitted = st.form_submit_button("Analyze & Save Job", use_container_width=True)

            if submitted:
                if not job_text.strip():
                    st.warning("Please paste job posting text.")
                else:
                    def llm_caller(sys_p: str, usr_p: str) -> str:
                        return call_llm(
                            system_prompt=sys_p,
                            user_prompt=usr_p,
                            api_key=settings.groq_api_key or "",
                            model=settings.llm_model,
                        )

                    with st.spinner("Analyzing job against your profile..."):
                        try:
                            job_id, record = process_job(
                                raw_text=job_text,
                                conn=conn,
                                profile_envelope=profile_envelope,
                                llm_caller=llm_caller,
                                llm_model=settings.llm_model,
                                source=job_source or "dashboard",
                                url=job_url or None,
                            )
                            st.success(
                                f"Job processed! (ID:{job_id}, Outcome:{record['outcome'].upper()})"
                            )
                            st.text(format_job_inspect(record))
                        except (ValueError, LLMError) as err:
                            st.error(f"Error processing job: {err}")
                        except Exception as err:
                            st.error(f"Unexpected error: {err}")