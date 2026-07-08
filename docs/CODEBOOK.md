# VIGIL Annotation Codebook (Gold-Standard Guidelines)

**Version:** 1.0 (DRAFT — freeze before annotation begins)
**Applies to:** Paper 1 — clinician-annotated benchmark of LLM vs rule-based AMR
information extraction.
**Frozen on:** __________ (fill the date you finalise this; do NOT edit rules
after inspecting model outputs — see §8).

> ⚠️ This document is the "answer key." It must be finalised **before** looking
> at any model output. Annotators label what the **text** supports, guided by the
> rules here — **not** by what any model produced.

---

## 1. Purpose & scope

Each document (a WHO/CDC/ECDC/UKHSA alert, a PubMed/preprint abstract, or a
ClinicalTrials record) is annotated with a set of structured labels. These human
labels are the **gold standard** against which every extraction method
(rule-based baseline, Gemini, other LLMs) is scored with per-field precision,
recall, F1, macro-F1, and inter-annotator κ.

**Focus (priority) pathogens:** CRE, VRE, MRSA (plus CRAB, CRKP, CRPA, ESBL,
_Candida auris_). Regional focus: **APAC**. Documents outside AMR/infectious
disease are marked *out-of-scope* and excluded.

**Annotated fields (the target schema):**

| Field | Type | Scored |
|---|---|---|
| `pathogens` | multi-label set | ✅ primary |
| `resistance_genes` | multi-label set | ✅ primary |
| `antibiotics` | multi-label set | ✅ primary |
| `diseases` | multi-label set | ✅ primary |
| `countries` | multi-label set | ✅ primary |
| `event_type` | single label (8 classes) | ✅ primary |
| `study_type` | single label | ✅ secondary |
| `summary` | free text | ✗ (assessed separately, not F1) |
| `keywords` | multi-label | ✗ (too subjective — excluded from scoring) |

`regions` is **derived** from `countries` (not annotated by hand).

---

## 2. Unit of annotation & general principles

1. **Document-level.** Label the document as a whole. You are answering: *"Which
   of these entities does this document substantively concern?"*
2. **沒寫 = 沒發生 (absence = 0).** If an entity is not mentioned, it is absent.
   Do not infer unstated entities from background knowledge.
3. **Substantive, not incidental.** Annotate an entity if it is a **subject** of
   the document (studied, reported, discussed). Do **not** annotate entities that
   appear only in passing background, reference lists, or boilerplate.
4. **Canonicalise.** Record the canonical label (see §4), not the surface string
   (e.g. text "meticillin-resistant *S. aureus*" → `MRSA`).
5. **Label the text, not the dictionary.** If a clinician sees a valid entity
   that is **not** in `extract/dictionaries.py` (e.g. a novel gene `MCR-10`, a
   pathogen like Hantavirus), you **still annotate it**. The gold standard must
   not be limited to the baseline's vocabulary, or the comparison is biased.
6. **When unsure, follow the examples**; if still unsure, leave a note and raise
   it at adjudication (§6) — do not guess silently.

---

## 3. Assertion handling (negation / speculation / history)

Decide, per mention, whether to annotate it:

| Assertion in text | Annotate? | Example |
|---|---|---|
| **Affirmed / studied** | ✅ Yes | "We report 12 CRE bloodstream infections" → CRE |
| **Primary subject even if negative finding** | ✅ Yes | "Screening for MRSA colonisation found none" → MRSA (MRSA is the study subject) |
| **Negated as incidental** | ❌ No | "…pneumonia (no MRSA isolated)…" where MRSA is a ruled-out aside → do **not** annotate MRSA |
| **Hypothetical / future / general background** | ❌ No | "CRE could spread in future" as background → No |
| **Historical, not this event** | ❌ No | "patient had prior VRE in 2019" in an unrelated report → No |
| **Drug list / method only, not studied** | ❌ No | an antibiotic named only inside a susceptibility-panel list, not analysed → No |

Rule of thumb: **is this entity part of what the document is actually about?**
If yes → annotate; if it's a ruled-out aside, background, or list item → skip.

---

## 4. Field-by-field definitions

### 4.1 `pathogens`
- **Include:** organisms and standard resistance-phenotype labels that the
  document concerns.
- **Canonical forms:** use phenotype labels where the text uses them —
  `MRSA`, `VRE`, `CRE`, `CRKP`, `CRAB`, `CRPA`, `ESBL`, `Candida auris`; otherwise
  the organism binomial (`Klebsiella pneumoniae`, `Escherichia coli`, …).
- **Phenotype + organism:** if the text names a resistance phenotype, annotate
  the phenotype (`MRSA`). Add the organism (`Staphylococcus aureus`) **only** if
  the organism is also discussed in its own right (e.g. both MSSA and MRSA).
  Do not mechanically add the organism for every phenotype.
- **Exclude:** viruses/pathogens mentioned only as background comparators.
- _Ex:_ "carbapenem-resistant *Klebsiella pneumoniae* (CRKP)" → `CRKP`, `CRE`
  (CRKP is a subtype of CRE — annotate both, they are distinct useful labels),
  and `Klebsiella pneumoniae` only if the species is separately discussed.

### 4.2 `resistance_genes` (genes & mechanisms)
- **Include:** carbapenemase/ESBL genes and resistance mechanisms —
  `NDM`, `KPC`, `OXA-48`, `OXA-23`, `VIM`, `IMP`, `CTX-M`, `mcr-1`, `vanA`,
  `vanB`, `mecA`, `carbapenemase`, `metallo-beta-lactamase`, etc.
- **Variants:** annotate the specific allele if named (`KPC-234`, `NDM-1`) AND
  its family (`KPC`, `NDM`). Record novel/unlisted genes verbatim (e.g. `MCR-10`).
- **Exclude:** generic phrases like "antibiotic resistance" with no
  gene/mechanism named.

### 4.3 `antibiotics` (incl. antifungals)
- **Include:** drugs that are studied, used, or tested as an outcome/intervention.
- **Canonical:** generic name, lower-case (`meropenem`, `ceftazidime-avibactam`,
  `cefiderocol`, `vancomycin`, `colistin`, `fluconazole`…).
- **Exclude:** drugs appearing only inside a routine susceptibility panel list
  that is not the paper's focus (per §3).

### 4.4 `diseases` / syndromes
- **Include:** the infection syndrome/clinical entity —
  `bloodstream infection`, `pneumonia`, `urinary tract infection`,
  `intra-abdominal infection`, `meningitis`, `endocarditis`, `wound infection`,
  `colonisation`, `candidemia`, `tuberculosis`, `outbreak`.
- Use `colonisation` (not infection) when the text specifies carriage/screening.

### 4.5 `countries`
- **Include** a country only if it is where the **event/study/cohort** actually
  occurred, or an explicitly involved location.
- **Author affiliation only ≠ country of the event** — do **not** annotate a
  country that appears solely in author affiliations unless the study was
  conducted there.
- **Canonical / aliases:** collapse `USA`/`United States of America` → `United
  States`; `England` → `United Kingdom`; `Korea` → `South Korea`;
  `Viet Nam` → `Vietnam`.
- Multi-country/"Global" outbreaks: annotate each named country.

### 4.6 `event_type` (choose exactly ONE, most specific)
Priority order when several could apply (higher wins):
1. **Outbreak** — an outbreak/epidemic/cluster is the subject (default for WHO
   DON and outbreak alerts).
2. **Clinical Trial** — a registered/prospective interventional trial.
3. **Guideline** — a guideline/recommendation/consensus/position statement.
4. **Vaccine** — primarily about a vaccine/vaccination.
5. **New Drug** — primarily about a novel antimicrobial / its activity/PK.
6. **Emerging Pathogen** — first report / newly identified organism or threat.
7. **Antimicrobial Resistance** — an AMR study not fitting the above.
8. **Research Article** — any other in-scope research paper (fallback).

### 4.7 `study_type` (choose ONE)
`Paper` · `Guideline` · `Clinical Trial` · `Outbreak` · `News`.

---

## 5. Out-of-scope documents
Mark a document **out-of-scope** (exclude from the benchmark) if it is not about
infectious disease or AMR at all (e.g. a materials-science paper that merely
mentions a bacterium as a test target with no ID/AMR content). Record the reason.

---

## 6. Annotation workflow

1. **Independent double annotation** of a **≥20% random subset** by a second
   annotator (blinded to the first) → for reliability (κ / agreement). The
   remaining documents are single-annotated by the primary annotator.
2. **Adjudication:** the two annotators (or a third senior adjudicator) resolve
   every disagreement in the double-annotated set; record the final consensus.
   Consensus labels become the gold standard for that subset.
3. **Log every rule clarification** in §10 (Changelog) — but only clarifications
   made **before** seeing model outputs (§8).
4. **Plausibility check:** flag implausible labels (e.g. a resistance gene with
   no organism) for review.

---

## 7. Inter-annotator agreement (report these)
- **Single-label fields** (`event_type`, `study_type`): **Cohen's κ**.
- **Multi-label entity fields** (`pathogens`, `genes`, `antibiotics`,
  `diseases`, `countries`): **pairwise micro-F1 between annotators**, and
  **Krippendorff's α** (treating each candidate entity as an item) where
  feasible.
- Report agreement **per field** and overall. Target κ/α ≥ 0.6 (substantial);
  investigate and refine (pre-freeze) if lower.

---

## 8. Leakage prevention (the freeze rule)
1. **Finalise this codebook AND `extract/dictionaries.py` before any model is
   run on the evaluation set.** Tag the frozen version (git tag / DOI).
2. **Do not** revise the codebook, dictionary, or gold labels in response to
   model outputs. If a genuine gap is found, revise **only** before performance
   is inspected, document it in §10, and **re-annotate affected documents
   consistently**.
3. Keep the annotation set and any prompt-development set **disjoint** — never
   tune prompts on the evaluation documents.
4. Store, for every model run, the model name/version, prompt version, and raw
   output (the platform already does this in the `extractions` table).

---

## 9. Worked example

> **Text (PubMed):** "Mechanisms underlying altered ceftazidime-avibactam
> resistance in *Klebsiella pneumoniae* driven by KPC-234 mutation and IncX3
> NDM-1 plasmid transfer. Four KPC-producing *K. pneumoniae* strains were
> isolated from one patient in China…"

**Gold labels:**
- `pathogens`: `CRKP`, `Klebsiella pneumoniae` (species is directly studied)
- `resistance_genes`: `KPC-234`, `KPC`, `NDM-1`, `NDM`
- `antibiotics`: `ceftazidime-avibactam`
- `diseases`: (none stated as a syndrome) → ∅
- `countries`: `China`
- `event_type`: `Antimicrobial Resistance` (mechanism study; not an outbreak
  report, not a trial)
- `study_type`: `Paper`

---

## 10. Changelog (pre-freeze clarifications only)
| Date | Rule changed | Reason |
|---|---|---|
| | initial draft | — |

---

_Once finalised, set the "Frozen on" date at the top, commit, and tag the
release. From that point the answer key is fixed._
