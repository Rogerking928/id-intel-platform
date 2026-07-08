# VIGIL: an open, automatically-updating platform for global antimicrobial-resistance and infectious-disease intelligence from open-source text

> **DRAFT preprint (resource descriptor).** Before posting: (1) regenerate the
> numbers below from the live platform (they update daily); (2) complete the
> reference list. Numbers here are from a snapshot of **2,075 documents**.

**Author.** Yen-Hsiang Wang, MD, MSc¹ · rogerwang890928@gmail.com ·
ORCID: [0000-0003-0307-8447](https://orcid.org/0000-0003-0307-8447)
¹ Graduate Institute of Medical Sciences, College of Medicine, Taipei Medical
University, Taipei 11031, Taiwan.

**Availability.** Code: https://github.com/Rogerking928/id-intel-platform ·
Archive/DOI: https://doi.org/10.5281/zenodo.21263882 ·
Live demo: https://id-intel-platform-4gkpazd4mhtj2upak5pzm9.streamlit.app/ ·
Licence: MIT.

---

## Abstract

**Background.** Antimicrobial resistance (AMR) and emerging infections generate
large volumes of open-source text — outbreak alerts, literature, trial
registries, surveillance reports — but converting them into structured,
comparable intelligence is largely manual. Existing event-based surveillance
systems focus on outbreak detection rather than AMR-specific, structured
extraction, and few are open, reproducible, or benchmarked against reference
data.

**Implementation.** VIGIL is a free, open-source platform that automatically
collects documents daily from eight source families (WHO Disease Outbreak News,
CDC, ECDC, UK Health Security Agency, PubMed, bioRxiv/medRxiv via Europe PMC,
ClinicalTrials.gov, and WHO GLASS/GHO), extracts a structured schema (pathogen,
resistance gene/mechanism, antibiotic, disease, country, event type) using an
always-on rule-based extractor and an optional large language model (LLM),
builds a co-occurrence knowledge graph, and computes trend, emerging-signal,
forecasting, novelty, and country-risk analytics. All analytics are validated
against WHO GHO/GLASS resistance indicators, which the platform ingests
automatically. The stack (Python, SQLite, Streamlit) is fully reproducible and
deploys for free; daily updates run via continuous integration.

**Results (proof of concept).** A snapshot of 2,075 documents across seven
actively-contributing sources yielded 31 distinct pathogens, 12 resistance
genes/mechanisms, 62 countries and 1,060 knowledge-graph relations, plus 1,005
WHO GHO reference resistance values (101 countries, 2016–2023). In a preliminary
construct-validity check across 23 countries, raw document volume was essentially
uncorrelated with measured MRSA resistance (Spearman ρ = 0.06) whereas a
publication-normalised AMR share showed a weak positive association (ρ = 0.28);
and literature signal did **not** discriminate which countries had officially
reported outbreaks (rank-AUC = 0.16), with outbreaks concentrated in
low-literature, lower-resource countries — an illustration of the global
surveillance gap that the platform makes measurable.

**Conclusions.** VIGIL provides an open, reproducible, validation-first
infrastructure for AMR/infectious-disease intelligence and a foundation for
downstream methodological research (LLM extraction benchmarking, early-warning
modelling). It is openly available with a citable DOI.

**Keywords.** antimicrobial resistance; infectious disease surveillance;
large language models; information extraction; knowledge graph; open data.

---

## 1. Background

[Motivate: AMR burden; open-source epidemic intelligence (WHO EIOS, HealthMap,
ProMED, EPIWATCH) targets outbreaks, not structured AMR extraction; LLMs offer
new extraction capability but need clinician-grounded, reproducible, benchmarked
tooling; gap = an open, AMR-focused, validation-first platform, with an
Asia-Pacific lens. — expand with references §8.]

## 2. Implementation

### 2.1 Architecture
Collector → extractor → entities/relations → analytics → web app. Single-file
SQLite store; every document retains raw text, source, URL and fetch time; every
extraction retains model name/version, prompt version and raw output, enabling
audit and model comparison.

### 2.2 Data sources
Eight configured source families (Table 1), accessed through public APIs/feeds:
WHO DON (OData), CDC/ECDC/UKHSA (RSS/Atom), PubMed (E-utilities), preprints
(Europe PMC), ClinicalTrials.gov (API v2), and WHO GHO/GLASS resistance
indicators (OData). Collection de-duplicates and appends only new records.

### 2.3 Information extraction
An always-on **rule-based** extractor uses frozen controlled vocabularies (the
codebook) and negation/assertion rules; an optional **LLM** extractor (Gemini;
extensible) returns the same schema. Both outputs are stored per document,
enabling head-to-head evaluation.

### 2.4 Knowledge graph and analytics
Entity co-occurrence within documents yields Pathogen→Country→Gene→Antibiotic→
Disease relations. Analytics include: growth-rate and emerging-signal detection;
weekly-volume forecasting with backtesting; novelty detection (first-ever entity
combinations); a knowledge-graph query interface; a global heatmap; a
validation-first country risk signal; and an outbreak module with
source-separated evaluation.

### 2.5 Validation design
Reference standard = WHO GHO/GLASS resistance indicators (auto-ingested).
Construct validity compares platform signals to measured resistance; the outbreak
task uses official-alert outcomes with literature-derived features (source
separation) to avoid circularity. A frozen annotation codebook supports a
downstream clinician-annotated extraction benchmark (leakage-controlled).

### 2.6 Availability & reproducibility
Open source (MIT), archived on Zenodo (DOI), free daily updates via CI, and a
public live instance. All code, the codebook, and the schema are versioned.

## 3. Results (proof of concept)
[Insert: corpus description (Table/Fig), extraction examples (e.g. detection of
KPC-234/NDM-1 that a dictionary misses), knowledge-graph example (CRE →
country → gene → antibiotic), and the preliminary validity numbers above.
Regenerate all numbers from the live platform before submission.]

## 4. Discussion
Positioning vs event-based systems; the measurable surveillance gap as an early
finding; enablement of reproducible LLM-extraction benchmarking and early-warning
research; APAC relevance.

## 5. Limitations
Young corpus (analytics strengthen as history accumulates); reporting/publication
bias (explicitly surfaced, not hidden); reference coverage — WHO GHO lacks some
territories including Taiwan (a WHO listing limitation, not a platform merge),
and China lacks values for these indicators; LLM free-tier throughput; the
extraction benchmark awaits full clinician annotation.

## 6. Conclusion
An open, validation-first platform turning open-source text into structured,
citable AMR/infectious-disease intelligence, and a base for a program of
methodological studies.

## 7. Declarations
**Data/code availability:** as above (GitHub + Zenodo DOI). **Funding:** _[fill]_.
**Competing interests:** none declared. **Ethics:** uses only open-source,
aggregate/public data; no individual patient data. **Author contributions:** YHW
conceived, built, and wrote.

## 8. References (verify & complete before submission)
- WHO. Global Antimicrobial Resistance and Use Surveillance System (GLASS). https://www.who.int/initiatives/glass
- WHO. Epidemic Intelligence from Open Sources (EIOS). https://www.who.int/initiatives/eios
- HealthMap. https://www.healthmap.org · ProMED-mail. https://promedmail.org · EPIWATCH (UNSW).
- WHO Global Health Observatory OData API. https://www.who.int/data/gho/info/gho-odata-api
- NCBI E-utilities; Europe PMC RESTful API; ClinicalTrials.gov API v2.
- _[Add: AMR burden (e.g. GBD AMR); NLP/LLM for clinical or surveillance information extraction; benchmarking of open LLMs.]_
