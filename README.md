# 🦠 Global AMR & Infectious Disease Intelligence Platform

**Author: Yen-Hsiang Wang, MD, MSc** · rogerwang890928@gmail.com

An **AI-driven** platform that automatically collects and analyses global infectious-disease
and antimicrobial-resistance (AMR) information every day. It is not a news aggregator — it
**extracts structured information, classifies it, builds knowledge relationships, and generates
trend analyses and weekly reports**, keeping the raw text and every model output so it can also
support downstream research and publication (Paper 1: an LLM AMR-extraction benchmark).

> Built entirely on free, open-source tools. No credit card required. It runs fully without any
> AI key (offline rule-based extraction); adding a free Gemini key upgrades the extraction.

---

## What it does (mapped to the requirements)

| Requirement | Feature | Location |
|---|---|---|
| Daily collection from WHO / CDC / ECDC / PubMed / ClinicalTrials / GLASS | 6 collectors | `collectors/` |
| AI extraction (pathogen, country, antibiotic, resistance gene, study type, summary…) | rule-based (always on) + Gemini (optional) | `extract/` |
| AI classification into 8 event categories | classifier | `extract/rule_based.py` |
| Knowledge relationships (Pathogen → Country → Gene → Antibiotic …) | entities + relations tables | `db.py`, Knowledge Graph page |
| AI trend analysis (most-discussed / fastest-rising / which countries…) | LLM- or template-generated | `analysis/trends.py` |
| Web dashboard (Today / Trend / Latest …) | multi-page Streamlit app | `app/` |
| Search (pathogen / country / antibiotic / gene / date / event type) | search page | `app/pages/1_*.py` |
| AI weekly report (Markdown / PDF export) | report generator | `analysis/weekly_report.py` |
| Prediction prototype (forecast a pathogen's next-N-weeks discussion volume) | transparent linear baseline + backtest | `analysis/forecast.py`, Forecast page |

---

## 1. Install (one-time)

You need **Python 3.10+**. Pick one path:

### Option A — Windows (simplest, recommended for beginners)

Open **PowerShell** and paste line by line:

```powershell
cd C:\Users\roger\Desktop\id-intel-platform
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Option B — WSL / Linux

```bash
cd /mnt/c/Users/roger/Desktop/id-intel-platform
# if venv is available:
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
# if you see "ensurepip is not available", use this instead:
pip install --user --break-system-packages -r requirements.txt
```

---

## 2. Update the data daily (collect + AI extraction)

```bash
python run_daily.py            # collect all sources, run AI extraction, build the knowledge graph
python run_daily.py --report   # same, plus generate the weekly report
```

The first run pulls more history (especially CDC); after that each run only adds new items
(automatic de-duplication).

To control volume (run faster), pass environment variables, e.g.:
```bash
PUBMED_MAX_PER_QUERY=10 WHO_MAX_ITEMS=15 python run_daily.py
```

---

## 3. Open the web dashboard

```bash
streamlit run app/Home.py
```

Your browser opens `http://localhost:8501`. The sidebar has five pages:

- **Home** — today's highlights, 30-day trend charts, latest publications / trials / guidelines
- **🔎 Search** — filter by pathogen / country / antibiotic / gene / event type / date; export CSV
- **📈 Trends** — AI trend analysis, fastest rising, time-series charts
- **🕸️ Knowledge Graph** — pick a pathogen, see the countries / genes / antibiotics / diseases it connects to
- **📰 Weekly Report** — one click to generate the report; download Markdown or HTML (print to PDF)

---

## 4. AI features (Gemini) — enabled

The platform **always** runs the free, offline rule-based extractor. If `.env` contains a
`GEMINI_API_KEY`, it **additionally** runs a Gemini extraction and makes that the version used by
search / knowledge graph / trend analysis.

- Get a key: <https://aistudio.google.com/apikey> (sign in with Google, no credit card). Click
  **Create API key** and copy it (new keys start with `AQ.`, older ones with `AIza`; both work).
- Paste it into `.env` (this project auto-loads `.env`, so you do **not** need `source .env`):
  ```
  GEMINI_API_KEY=your_key
  GEMINI_MODEL=gemini-2.5-flash
  ```
- Then run `python run_daily.py` as usual and AI turns on automatically.

**Free-tier throttling (important):** the free tier limits requests per minute, so each run
processes at most `GEMINI_MAX_PER_RUN=50` documents with an LLM extraction, spaced by
`GEMINI_MIN_INTERVAL=4.5` seconds. Raise the cap to do more at once:
```bash
GEMINI_MAX_PER_RUN=200 python run_daily.py
```
Scheduling it daily works through the backlog over time. Every document keeps **both** the
rule-based and Gemini extractions — exactly the model-comparison data Paper 1 needs (in testing,
Gemini captured details the rule-based extractor missed, e.g. `KPC-234`, `NDM-1`, plasmid types).

---

## 5. Run it automatically every day

**WSL / Linux (cron)** — 07:00 every day:
```
0 7 * * * cd /mnt/c/Users/roger/Desktop/id-intel-platform && /usr/bin/python3 run_daily.py --report >> data/cron.log 2>&1
```
Add it with `crontab -e`.

**Windows (Task Scheduler):** create a daily task — program `py`, arguments
`run_daily.py --report`, start-in set to the project folder.

**Free cloud (GitHub Actions):** `.github/workflows/daily.yml` is included. Push the repo to
GitHub, add `GEMINI_API_KEY` under Settings → Secrets and variables → Actions, and it runs daily
in the cloud (even when your computer is off), committing the refreshed database back to the repo.

---

## Project structure

```
id-intel-platform/
├─ run_daily.py          # ★ one command: collect → extract → classify → knowledge graph (schedulable)
├─ config.py             # all settings (pathogens to track, queries, volume limits…)
├─ db.py                 # SQLite database (documents / extractions / entities / relations / annotations)
├─ requirements.txt
├─ .env.example          # optional key template
├─ collectors/           # six data sources
│  ├─ pubmed.py  clinicaltrials.py  who.py  rss.py (CDC/ECDC)  glass.py
├─ extract/              # AI extraction
│  ├─ dictionaries.py    # controlled vocabularies (pathogen/antibiotic/gene/country) = Paper 1 codebook
│  ├─ rule_based.py      # rule-based extractor (always on; also the paper's baseline)
│  ├─ llm.py             # Gemini extractor (optional)
│  └─ pipeline.py        # extraction flow + knowledge-graph build
├─ analysis/
│  ├─ trends.py          # trend analysis (incl. AI narrative)
│  └─ weekly_report.py   # weekly report (Markdown + HTML)
├─ app/                  # Streamlit web app
│  ├─ Home.py  common.py  pages/…
├─ data/                 # SQLite file (auto-created)
└─ reports/              # generated weekly reports
```

---

## How this supports the research (Paper 1)

Every document keeps: **raw_text + source + URL + fetch time + model name/version/prompt version/raw
output**. The `annotations` table holds your (and a second annotator's) gold-standard labels, so you
can later compute per-field F1, macro-F1, and κ, comparing rule-based vs a free LLM on AMR extraction
for CRE / VRE / MRSA.

> ⚠️ To avoid data leakage: freeze `extract/dictionaries.py` (the codebook) and the schema **before**
> looking at model outputs and annotating.

---

## Roadmap (beyond the MVP)

A true Neo4j knowledge graph, AI trend/hotspot forecasting, cross-country guideline comparison, an
interactive global AMR map, a public research API, and automated systematic-review support. The
current architecture (collector → extractor → entities/relations → analysis → app) already leaves
room for these.
