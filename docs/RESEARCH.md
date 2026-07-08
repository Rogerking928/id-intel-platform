# VIGIL — Research Blueprint

Platform: **VIGIL** (Global AMR & Infectious Disease Intelligence Platform).
DOI: 10.5281/zenodo.21263882 · Author: Yen-Hsiang Wang, MD, MSc.

**Positioning.** VIGIL is not a news aggregator. It is a research instrument that
turns open-source infectious-disease/AMR text into structured, validated
intelligence. One platform → a program of complementary papers. Regional focus:
**APAC**; priority pathogens: **CRE / VRE / MRSA** (+ CRAB, _C. auris_).

---

## Paper 1 (flagship, do first) — LLM vs rule-based AMR information extraction

**Working title.** *Can free, open large language models extract antimicrobial-
resistance intelligence from open-source text? A clinician-annotated benchmark
(CRE/VRE/MRSA, Asia-Pacific).*

**Gap / novelty.** AMR surveillance is text-rich but extraction is manual. Prior
NLP work is mostly English clinical notes or proprietary models. Missing:
a **clinician-annotated** benchmark of **free/accessible** LLMs for **structured
AMR entity extraction**, with a **regional (APAC)** lens. VIGIL fills all three.

**Research questions.**
- RQ1. How accurately do free LLMs (Gemini free tier; later Llama-via-Groq, local
  Ollama) extract pathogen / resistance-gene / antibiotic / disease / country /
  event-type vs a dictionary+rule baseline?
- RQ2. Which fields are hard (e.g. gene alleles, event classification)?
- RQ3. Do LLMs recover entities outside the baseline dictionary (novel genes)?

**Data.** A frozen sample of VIGIL documents (target **~300**, stratified across
sources and the priority pathogens). Every document already stores raw_text +
source + fetch time; every model run stores model/version/prompt/raw output.

**Gold standard.** Clinician annotation per `docs/CODEBOOK.md` (frozen before
model inspection). **≥20%** double-annotated by a second annotator for
reliability. Adjudicated consensus = gold.

**Comparators.** `rule_based` baseline vs `gemini-2.5-flash` (+ add ≥1 more model
for a stronger benchmark). All already wired into the ✍️ Annotate / 📐 Benchmark
pages.

**Metrics.** Per-field precision/recall/F1, macro-F1; Cohen's κ (single-label)
and pairwise F1 / Krippendorff α (multi-label) for inter-annotator agreement.
Error analysis by field and pathogen.

**Analysis.** The 📐 Benchmark page produces the core results table directly.

**Target venues.** JAMIA · JMIR Public Health & Surveillance · PLOS Digital
Health. (Preprint on **medRxiv** at submission.)

**Feasibility / bottleneck.** Software done. Bottleneck = the ~300-document
clinician annotation (only you can do it) + recruiting a second annotator.

**Risks & mitigation.** Small n → widen sample; leakage → freeze codebook (§8);
free-tier quota → batch LLM runs daily (already handled).

---

## Paper 2 (higher-impact, needs accumulated data) — the surveillance gap / early warning

**Working title.** *Open-source literature signals do not track where AMR and
outbreaks occur: quantifying the global surveillance gap, and what a valid
early-warning signal requires.*

**Hook (already observed in VIGIL).** Raw literature volume correlates near-zero
with WHO GLASS measured resistance (Spearman ≈ 0.06) and *inversely* with where
official outbreaks occur (rank-AUC ≈ 0.16) — outbreaks cluster in low-literature,
low-resource countries. This is a real, publishable finding about reporting bias.

**Aims.** (1) Quantify the gap across countries/income strata and pathogens,
validated against WHO GHO/GLASS. (2) Test whether normalised / velocity /
spillover signals (not raw volume) achieve lead time vs official alerts.

**Validation.** Temporal (no-leakage) design; AUROC/AUPRC, calibration, lead-time
vs GLASS/DON; beat a persistence baseline; income-stratified + leave-one-source-
out sensitivity. Ground truth auto-fetched (WHO GHO, already ingested).

**Status.** Framework built (Risk / Outbreak / Forecast pages). Needs the daily
auto-update to accumulate months of history — **running now**.

**Target venues.** Lancet Digital Health / eClinicalMedicine (stretch) · JMIR PHS
· PLOS Global Public Health.

---

## Paper 3 (citation magnet) — resource / dataset descriptor

**Working title.** *VIGIL: an open, automatically-updating platform and dataset
for global AMR & infectious-disease intelligence.*

**Content.** Architecture, sources, extraction schema, the open annotated
dataset (Zenodo, CC-BY), reproducibility. Descriptor papers are easy to publish
and accrue citations whenever others reuse the tool/data.

**Target venues.** JOSS · GigaScience/Database · Scientific Data · JMIR.

---

## Cross-cutting strategy

**Increase citations.** Open code + DOI (done) → CC-BY dataset → medRxiv preprint
early → reusable benchmark/leaderboard → keyworded titles → ORCID + Scholar →
a networked co-author (e.g. an APAC AMR group such as ACORN) → conference
(ECCMID/IDWeek/AMIA) + a social thread on the surveillance-gap finding.

**Open science.** Freeze codebook + dictionaries before evaluation; publish the
gold standard and prompts; version everything (git tags + Zenodo).

**Authorship / ethics.** All data are open-source/aggregate (no patient data →
minimal IRB burden; confirm with your institution). Define authorship &
second-annotator credit up front.

**Suggested sequence.**
1. Now: freeze codebook → annotate ~300 (Paper 1) while data accumulates.
2. +3–6 mo: Paper 1 submitted; enough history for Paper 2 analysis.
3. Alongside: Paper 3 descriptor (low effort, high reuse).

**Immediate next actions.**
- [ ] Get an ORCID (orcid.org) → add to `CITATION.cff`.
- [ ] Finalise & freeze `docs/CODEBOOK.md` (set the freeze date, tag it).
- [ ] Pick the ~300-document annotation sample (stratified).
- [ ] Recruit the second annotator.
- [ ] Start annotating on the ✍️ Annotate page.
