"""Weekly Report page — generate and download the Global AMR & ID Weekly Report."""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from common import page_setup  # noqa: E402
from analysis import weekly_report  # noqa: E402

page_setup("Weekly Report", "📰")
st.title("📰 Global AMR & Infectious Disease Weekly Report")

days = st.slider("Report window (days)", 7, 30, 7)

if st.button("🪄 Generate report", type="primary"):
    with st.spinner("Generating (this calls the AI narrative if configured)…"):
        out = weekly_report.generate(days=days)
    st.success(f"Saved to {out['html']}")
    st.session_state["report_md"] = out["content"]
    st.session_state["report_html_path"] = out["html"]

md = st.session_state.get("report_md")
if md:
    c1, c2 = st.columns(2)
    c1.download_button("⬇️ Download Markdown", md, "weekly_report.md", "text/markdown")
    html_path = st.session_state.get("report_html_path")
    if html_path and Path(html_path).exists():
        c2.download_button("⬇️ Download HTML (print → PDF)",
                           Path(html_path).read_text(encoding="utf-8"),
                           "weekly_report.html", "text/html")
    st.divider()
    st.markdown(md)
else:
    st.info("Click **Generate report** to build this week's report. "
            "To get a PDF, download the HTML and use your browser's "
            "Print → Save as PDF.")
