"""Streamlit UI for interactive resume–JD matching."""

from __future__ import annotations

import streamlit as st

from src.container import get_resume_matching_service


def run() -> None:
    """Render the Streamlit app and handle user interactions."""
    st.set_page_config(page_title="Resume Matcher", layout="wide")
    st.title("Resumer Shortlister")

    jd_text = st.text_area("Paste Job Description here", height=200)
    resume_files = st.file_uploader(
        "Upload Resumes (PDF, DOCX, or TXT)",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
    )

    if jd_text and resume_files:
        svc = get_resume_matching_service()
        files = [(f.name, f.getvalue()) for f in resume_files]
        results = svc.match_files(jd_text=jd_text, files=files)

        st.subheader("Results")
        for res in results:
            st.markdown(f"### {res.get('filename', 'Resume')}")
            st.write(f"**Match %:** {res.get('match_percentage', 0)}%")
            st.write(f"**Summary:** {res.get('summary', 'No summary returned.')}")

            skills = res.get("skills") or []
            if isinstance(skills, list):
                skills_list = skills
            else:
                skills_list = [s.strip() for s in str(skills).split(",") if s.strip()]

            if skills_list:
                st.write("**Skills:**")
                st.write(", ".join(skills_list))

            recommendations = res.get("recommendations")
            if recommendations:
                st.write("**Recommendations:**")
                st.write(recommendations)

            weaknesses = res.get("weaknesses")
            if weaknesses:
                st.write("**Weaknesses:**")
                st.write(weaknesses)

            if res.get("match_percentage", 0) >= 80:
                st.success("✅ Shortlisted (≥ 80% match)")
            else:
                st.warning("⚠️ Not shortlisted (< 80% match)")


if __name__ == "__main__":
    run()
