# VIGIL Paper 1 — Annotator Quick-Start

This is the 5-minute quick-start. The **rules for every label** live in
[`CODEBOOK.md`](CODEBOOK.md) — that document is the answer key; this one just tells
you how to run the workflow.

> **Golden rule (leakage):** label what the **text** supports, guided by the
> codebook — never by what a model produced. Model output is hidden in the tool on
> purpose. The codebook must be **frozen** (dated, unchanged) before you start.

---

## 1. What you are annotating

A single **frozen gold sample of 150 documents** (`docs/gold_sample.csv`), the same
set for every annotator — this is what makes inter-annotator agreement (Cohen's κ)
and the benchmark valid. It is built reproducibly:

```bash
python -m analysis.gold_sample     # writes docs/gold_sample.csv (only run once, then commit)
```

## 2. Annotate

```bash
streamlit run app/Home.py          # then open the ✍️ Annotate page
```

1. Type **your annotator name** (each annotator uses their own; both label the same
   150 docs).
2. Keep **"Gold sample only"** ticked.
3. For each document, read the full text and fill each field **from the text**:
   - **Entities** (multi-label): pathogens, resistance genes/mechanisms, antibiotics,
     diseases, countries *(event location, not author affiliation — codebook §2.4)*.
     Pick from the list; add anything missing in the "…other" box per codebook §2.5.
   - **Classification** (single-label): event type, study type. Tick **Out of scope**
     for non-ID/non-AMR documents (codebook §1).
4. Click **💾 Save annotation**. It advances to the next document.

Target: ~150 docs. A second colleague annotates the **same** set independently — do
not discuss individual documents until both are done (that protects κ).

## 3. Score the benchmark

Once the LLM has processed the gold docs (below), and you have annotations:

```bash
python -m analysis.run_benchmark                          # F1: rule-based vs LLM vs gold
python -m analysis.run_benchmark --annotator YOU --second COLLEAGUE   # adds Cohen's κ
```

Output (per-field precision/recall/F1, macro-F1, and κ) is printed and written to
`reports/benchmark_<date>/`.

## 4. Make sure the LLM has seen the gold docs

The benchmark compares the LLM against your labels, so the LLM must have processed
the **same** documents. Gemini's free tier is rate-limited, so this is capped and
resumable — run it on successive days until coverage is complete:

```bash
python extract_gold_llm.py         # processes up to GEMINI_MAX_PER_RUN gold docs
```

The rule-based baseline already covers every document, so it needs no extra step.

---

### Checklist before you call the benchmark "done"
- [ ] `CODEBOOK.md` frozen and dated
- [ ] `docs/gold_sample.csv` built and committed (never re-drawn after annotation starts)
- [ ] both annotators finished all 150 docs
- [ ] `extract_gold_llm.py` shows full gold LLM coverage
- [ ] `run_benchmark.py` reports κ and per-field F1
