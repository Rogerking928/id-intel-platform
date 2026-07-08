"""
Annotate page (Paper 1) — build the clinician gold standard.

Shows one document at a time and lets you label each field per the codebook
(docs/CODEBOOK.md). Model outputs are deliberately NOT shown here, to avoid
anchoring your labels (leakage). Labels are saved to the `annotations` table.
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from common import page_setup  # noqa: E402
import db  # noqa: E402
from extract import dictionaries as dic  # noqa: E402
from extract.dictionaries import canonical_country  # noqa: E402

page_setup("Annotate", "✍️")
st.title("✍️ Gold-standard Annotation")
st.caption("Label documents per docs/CODEBOOK.md. Model output is hidden on "
           "purpose so it can't bias you. Your labels build the Paper 1 benchmark.")

VOCAB = {
    "pathogens": sorted(dic.PATHOGENS.keys()),
    "resistance_genes": sorted(dic.RESISTANCE_GENES.keys()),
    "antibiotics": sorted(dic.ANTIBIOTICS.keys()),
    "diseases": sorted(dic.DISEASES.keys()),
    "countries": sorted({canonical_country(c) for c in dic.COUNTRY_REGION}),
}
EVENT_TYPES = dic.EVENT_TYPE_ORDER
STUDY_TYPES = ["Paper", "Guideline", "Clinical Trial", "Outbreak", "News"]

annotator = st.text_input("Your annotator name (used for κ / double-annotation)",
                          value=st.session_state.get("annotator", ""))
st.session_state["annotator"] = annotator
if not annotator.strip():
    st.info("Enter your annotator name to begin.")
    st.stop()

# --- document picker ---------------------------------------------------------
with db.get_conn() as conn:
    docs = [dict(r) for r in conn.execute(
        "SELECT id, source, title FROM documents ORDER BY id").fetchall()]
done = db.annotated_document_ids(annotator)
c1, c2 = st.columns([3, 1])
hide_done = c2.checkbox("Hide done", value=True)
pool = [d for d in docs if not (hide_done and d["id"] in done)]
st.progress(len(done) / len(docs) if docs else 0,
            text=f"Annotated by you: {len(done)} / {len(docs)} documents")
if not pool:
    st.success("Nothing left to annotate in this view. Uncheck 'Hide done' to review.")
    st.stop()

def _label(d):
    mark = "✓ " if d["id"] in done else ""
    return f"{mark}#{d['id']} · {d['source']} · {(d['title'] or '')[:70]}"

pick = c1.selectbox("Document", pool, format_func=_label,
                    index=min(st.session_state.get("apos", 0), len(pool) - 1))
doc_id = pick["id"]
with db.get_conn() as conn:
    full = dict(conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone())

st.markdown(f"#### [{full['title']}]({full['url']})")
st.caption(f"{full['source']} · {full.get('published_date') or ''}")
with st.expander("📄 Full text", expanded=True):
    st.write(full["raw_text"] or "")

# --- annotation form ---------------------------------------------------------
existing = db.get_annotation_set(doc_id, annotator)


def field_widget(field, label):
    opts = VOCAB[field]
    prior = existing.get(field, [])
    default = [v for v in prior if v in opts]
    other_prior = [v for v in prior if v not in opts]
    sel = st.multiselect(label, opts, default=default, key=f"{field}_{doc_id}")
    other = st.text_input(f"…other {field.replace('_',' ')} (comma-separated, per codebook §2.5)",
                          value=", ".join(other_prior), key=f"{field}_o_{doc_id}")
    extra = [x.strip() for x in other.split(",") if x.strip()]
    return sel + extra


st.markdown("##### Entities")
data = {}
data["pathogens"] = field_widget("pathogens", "Pathogens")
data["resistance_genes"] = field_widget("resistance_genes", "Resistance genes / mechanisms")
data["antibiotics"] = field_widget("antibiotics", "Antibiotics / antifungals")
data["diseases"] = field_widget("diseases", "Diseases / syndromes")
data["countries"] = field_widget("countries", "Countries (event location, not affiliation)")

st.markdown("##### Classification")
cc1, cc2, cc3 = st.columns(3)
ev_prior = (existing.get("event_type") or [None])[0]
sy_prior = (existing.get("study_type") or [None])[0]
data["event_type"] = cc1.selectbox("Event type", EVENT_TYPES,
                                    index=EVENT_TYPES.index(ev_prior) if ev_prior in EVENT_TYPES else len(EVENT_TYPES) - 1)
data["study_type"] = cc2.selectbox("Study type", STUDY_TYPES,
                                   index=STUDY_TYPES.index(sy_prior) if sy_prior in STUDY_TYPES else 0)
out_of_scope = cc3.checkbox("Out of scope", value=("out" in existing.get("_scope", [])))
if out_of_scope:
    data["_scope"] = "out"

if st.button("💾 Save annotation", type="primary"):
    db.save_annotation_set(doc_id, annotator, data)
    st.session_state["apos"] = min(st.session_state.get("apos", 0) + 1, len(pool) - 1)
    st.success(f"Saved #{doc_id}. Moving to the next document…")
    st.rerun()
