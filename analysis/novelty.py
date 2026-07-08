"""
Novelty detector (Phase 4 — "new knowledge discovery", not news aggregation).

Idea: a finding is interesting not because it is frequent, but because it is
NEW. We detect entity combinations (e.g. resistance-gene + pathogen + country)
that appear in a recent document but have NEVER co-occurred in any earlier
document in the corpus.

    First time  MCR-10  +  Salmonella  +  Vietnam   ->  🧬 Novel finding

This is combinatorial novelty on the knowledge graph — fully interpretable and
free (no model needed). It sharpens as the historical corpus grows: with only a
young corpus almost everything looks novel, so the baseline matters. Roadmap:
add embedding-based semantic novelty (document vs 3-year corpus) alongside this.
"""
from __future__ import annotations

from datetime import date, timedelta
from itertools import combinations

import db

DATE_EXPR = "COALESCE(NULLIF(d.published_date,''), substr(d.fetched_at,1,10))"

# Which entity-type combinations count as an interesting "finding".
PAIR_TYPES = [
    ("resistance_gene", "pathogen"),
    ("resistance_gene", "country"),
    ("pathogen", "country"),
    ("antibiotic", "pathogen"),
]
TRIPLE_TYPES = [("resistance_gene", "pathogen", "country")]


def _load_docs():
    """doc_id -> {'day':.., 'ents':{type:set(values)}, 'title','url','source'}"""
    docs = {}
    with db.get_conn() as conn:
        for r in conn.execute(
            f"""SELECT d.id, d.title, d.url, d.source, {DATE_EXPR} AS day
                FROM documents d"""):
            docs[r["id"]] = {"day": r["day"], "title": r["title"], "url": r["url"],
                             "source": r["source"], "ents": {}}
        from extract.dictionaries import canonical_country
        for r in conn.execute("SELECT document_id, entity_type, value FROM entities"):
            d = docs.get(r["document_id"])
            if d is not None:
                val = canonical_country(r["value"]) if r["entity_type"] == "country" else r["value"]
                d["ents"].setdefault(r["entity_type"], set()).add(val)
    return docs


def _combos_for_doc(ents: dict):
    """Yield (frozenset-of-typed-values, label-tuple) for each configured combo."""
    for ta, tb in PAIR_TYPES:
        for a in ents.get(ta, ()):
            for b in ents.get(tb, ()):
                yield (frozenset([(ta, a), (tb, b)]), (a, b))
    for ta, tb, tc in TRIPLE_TYPES:
        for a in ents.get(ta, ()):
            for b in ents.get(tb, ()):
                for c in ents.get(tc, ()):
                    yield (frozenset([(ta, a), (tb, b), (tc, c)]), (a, b, c))


def novel_findings(recent_days: int = 30, limit: int = 40) -> list[dict]:
    """Combinations appearing in the recent window but in no earlier document."""
    docs = _load_docs()
    cutoff = (date.today() - timedelta(days=recent_days)).isoformat()

    historical = set()
    recent_docs = []
    for did, d in docs.items():
        day = d["day"] or ""
        combos = list(_combos_for_doc(d["ents"]))
        if day < cutoff:
            for key, _label in combos:
                historical.add(key)
        else:
            recent_docs.append((day, did, d, combos))

    seen, findings = set(), []
    for day, did, d, combos in sorted(recent_docs, reverse=True):
        for key, label in combos:
            if key in historical or key in seen:
                continue
            seen.add(key)
            findings.append({
                "combination": " + ".join(label),
                "size": len(label),
                "day": day,
                "title": d["title"],
                "url": d["url"],
                "source": d["source"],
            })
    # richer combinations (triples) first, then most recent
    findings.sort(key=lambda f: (f["size"], f["day"]), reverse=True)
    return findings[:limit]


if __name__ == "__main__":
    for f in novel_findings()[:15]:
        print(f"[{f['day']}] {f['combination']}   ({f['source']}) {(f['title'] or '')[:50]}")
