"""
Paper 1 scoring engine.

Compares each extractor (rule_based baseline, Gemini, …) against the
clinician gold standard stored in the `annotations` table, reporting per-field
precision / recall / F1 and macro-F1, plus inter-annotator agreement (Cohen's κ
for single-label fields, micro-F1 for multi-label fields).

No scipy/sklearn — everything is computed directly so it runs on Streamlit Cloud.
"""
from __future__ import annotations

import json

import pandas as pd

import db
from extract.dictionaries import canonical_country

MULTI_FIELDS = ["pathogens", "resistance_genes", "antibiotics", "diseases", "countries"]
SINGLE_FIELDS = ["event_type", "study_type"]
ALL_FIELDS = MULTI_FIELDS + SINGLE_FIELDS


def _canon(field: str, values) -> set:
    vals = {str(v).strip() for v in values if str(v).strip()}
    if field == "countries":
        vals = {canonical_country(v) for v in vals}
    return {v.lower() if field != "countries" else canonical_country(v) for v in vals}


def gold_map(annotator: str) -> dict:
    """{document_id: {field: set(values)}} from one annotator's labels."""
    out: dict = {}
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT document_id, field, value FROM annotations WHERE annotator=?",
            (annotator,)).fetchall()
    for r in rows:
        out.setdefault(r["document_id"], {}).setdefault(r["field"], set()).add(r["value"])
    # normalise
    for did, fields in out.items():
        for f in list(fields):
            fields[f] = _canon(f, fields[f])
    return out


def extractor_map(extractor: str) -> dict:
    """{document_id: {field: set(values)}} from an extractor's stored output."""
    out: dict = {}
    with db.get_conn() as conn:
        rows = conn.execute(
            f"""SELECT document_id, {','.join(MULTI_FIELDS)}, event_type, study_type
                FROM extractions WHERE extractor=?""", (extractor,)).fetchall()
    for r in rows:
        rec = {}
        for f in MULTI_FIELDS:
            try:
                rec[f] = _canon(f, json.loads(r[f] or "[]"))
            except Exception:
                rec[f] = set()
        rec["event_type"] = _canon("event_type", [r["event_type"]]) if r["event_type"] else set()
        rec["study_type"] = _canon("study_type", [r["study_type"]]) if r["study_type"] else set()
        out[r["document_id"]] = rec
    return out


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return round(p, 3), round(r, 3), round(f, 3)


def score(annotator: str, extractor: str) -> dict:
    gold = gold_map(annotator)
    pred = extractor_map(extractor)
    docs = [d for d in gold if d in pred]
    rows, f1s = [], []
    for field in ALL_FIELDS:
        tp = fp = fn = 0
        for d in docs:
            g = gold[d].get(field, set())
            p = pred[d].get(field, set())
            tp += len(g & p)
            fp += len(p - g)
            fn += len(g - p)
        P, R, F1 = _prf(tp, fp, fn)
        rows.append({"field": field, "precision": P, "recall": R, "F1": F1,
                     "gold_items": tp + fn})
        f1s.append(F1)
    macro = round(sum(f1s) / len(f1s), 3) if f1s else 0.0
    return {"n_docs": len(docs), "per_field": pd.DataFrame(rows), "macro_f1": macro}


def compare(annotator: str, extractors: list[str]) -> pd.DataFrame:
    """Side-by-side F1 per field for several extractors."""
    frames = {}
    n = 0
    for ex in extractors:
        s = score(annotator, ex)
        n = s["n_docs"]
        frames[ex] = s["per_field"].set_index("field")["F1"]
        frames[ex + "_"] = s  # keep macro
    if not frames:
        return pd.DataFrame()
    table = pd.DataFrame({ex: frames[ex] for ex in extractors})
    macro = {ex: score(annotator, ex)["macro_f1"] for ex in extractors}
    table.loc["MACRO-F1"] = pd.Series(macro)
    table.attrs["n_docs"] = n
    return table


# --- inter-annotator agreement ----------------------------------------------
def _cohen_kappa(pairs: list[tuple[str, str]]) -> float | None:
    if not pairs:
        return None
    labels = sorted({x for pr in pairs for x in pr})
    n = len(pairs)
    po = sum(1 for a, b in pairs if a == b) / n
    pe = 0.0
    for lab in labels:
        pa = sum(1 for a, _ in pairs if a == lab) / n
        pb = sum(1 for _, b in pairs if b == lab) / n
        pe += pa * pb
    if pe >= 1.0:
        return 1.0
    return round((po - pe) / (1 - pe), 3)


def inter_annotator(a1: str, a2: str) -> pd.DataFrame:
    g1, g2 = gold_map(a1), gold_map(a2)
    docs = [d for d in g1 if d in g2]
    rows = []
    for field in ALL_FIELDS:
        if field in MULTI_FIELDS:
            tp = fp = fn = 0
            for d in docs:
                s1, s2 = g1[d].get(field, set()), g2[d].get(field, set())
                tp += len(s1 & s2); fp += len(s2 - s1); fn += len(s1 - s2)
            _, _, f1 = _prf(tp, fp, fn)
            rows.append({"field": field, "agreement (F1)": f1, "kappa": "—"})
        else:
            pairs = []
            for d in docs:
                a = next(iter(g1[d].get(field, {"∅"})), "∅")
                b = next(iter(g2[d].get(field, {"∅"})), "∅")
                pairs.append((a, b))
            k = _cohen_kappa(pairs)
            acc = round(sum(1 for a, b in pairs if a == b) / len(pairs), 3) if pairs else 0
            rows.append({"field": field, "agreement (F1)": acc, "kappa": k})
    df = pd.DataFrame(rows)
    df.attrs["n_docs"] = len(docs)
    return df


def export_gold(annotator: str) -> pd.DataFrame:
    gm = gold_map(annotator)
    rows = []
    for did, fields in gm.items():
        rec = {"document_id": did}
        for f in ALL_FIELDS:
            rec[f] = "; ".join(sorted(fields.get(f, set())))
        rows.append(rec)
    return pd.DataFrame(rows).sort_values("document_id")
