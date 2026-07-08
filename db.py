"""
SQLite storage layer.

Design rules (these serve Paper 1 as well as the platform):
  * Every document keeps raw_text + source + url + fetched_at  -> reproducible.
  * Every extraction records extractor + model_version + prompt_version +
    raw_output  -> you can compare rule-based vs Gemini and audit any field.
  * entities / relations are DERIVED from the "active" extraction, so search
    and the knowledge graph stay fast and simple.

No external database server needed: this is a single file under data/.
"""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    source         TEXT NOT NULL,          -- WHO, CDC, ECDC, PubMed, ClinicalTrials, GLASS
    source_id      TEXT NOT NULL,          -- PMID / NCT id / DON UrlName / feed guid
    url            TEXT,
    title          TEXT,
    raw_text       TEXT,                   -- abstract / summary / body
    published_date TEXT,                   -- ISO date (YYYY-MM-DD) when known
    fetched_at     TEXT NOT NULL,          -- ISO timestamp of collection
    lang           TEXT DEFAULT 'en',
    UNIQUE(source, source_id)
);

CREATE TABLE IF NOT EXISTS extractions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id    INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    extractor      TEXT NOT NULL,          -- e.g. rule_based / gemini-2.0-flash
    model_version  TEXT,
    prompt_version TEXT,
    created_at     TEXT NOT NULL,
    summary        TEXT,
    event_type     TEXT,                   -- Outbreak / AMR / ... (classification)
    study_type     TEXT,                   -- Paper / Guideline / Clinical Trial / Outbreak
    countries      TEXT,                   -- JSON list
    regions        TEXT,                   -- JSON list
    pathogens      TEXT,                   -- JSON list
    diseases       TEXT,                   -- JSON list
    antibiotics    TEXT,                   -- JSON list
    resistance_genes TEXT,                 -- JSON list
    keywords       TEXT,                   -- JSON list
    raw_output     TEXT,                   -- full raw model output (audit)
    is_active      INTEGER DEFAULT 0,      -- 1 = the extraction feeding search/graph
    UNIQUE(document_id, extractor, model_version, prompt_version)
);

CREATE TABLE IF NOT EXISTS entities (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id  INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    entity_type  TEXT NOT NULL,            -- pathogen / country / antibiotic / resistance_gene / disease / region / event_type
    value        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_entities_type_value ON entities(entity_type, value);
CREATE INDEX IF NOT EXISTS idx_entities_doc ON entities(document_id);

CREATE TABLE IF NOT EXISTS relations (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id  INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    src_type     TEXT NOT NULL,
    src_value    TEXT NOT NULL,
    dst_type     TEXT NOT NULL,
    dst_value    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_relations_src ON relations(src_type, src_value);
CREATE INDEX IF NOT EXISTS idx_relations_dst ON relations(dst_type, dst_value);

-- Gold-standard human annotations for Paper 1 (kept separate from model output).
CREATE TABLE IF NOT EXISTS annotations (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id  INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    annotator    TEXT NOT NULL,
    field        TEXT NOT NULL,
    value        TEXT,
    created_at   TEXT NOT NULL
);

-- External AMR resistance reference data (WHO GHO / GLASS-derived indicators),
-- used as ground truth for validating the risk score. country-year-indicator.
CREATE TABLE IF NOT EXISTS amr_reference (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    country_iso3 TEXT NOT NULL,
    country      TEXT,
    indicator    TEXT NOT NULL,          -- e.g. AMR_INFECT_MRSA
    year         INTEGER,
    value        REAL,                   -- resistance %
    source       TEXT DEFAULT 'WHO GHO',
    UNIQUE(country_iso3, indicator, year)
);

-- Simple log so you can see what each daily run did.
CREATE TABLE IF NOT EXISTS run_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at   TEXT,
    finished_at  TEXT,
    summary      TEXT
);
"""

JSON_FIELDS = [
    "countries", "regions", "pathogens", "diseases",
    "antibiotics", "resistance_genes", "keywords",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def get_conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # synchronous=NORMAL keeps durability sane while cutting the fsync cost that
    # makes writes crawl on Windows-mounted (drvfs) volumes.
    conn.execute("PRAGMA synchronous = NORMAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------
def upsert_document(doc: dict) -> tuple[int, bool]:
    """
    Insert a document if new. Returns (document_id, is_new).
    `doc` needs: source, source_id, url, title, raw_text, published_date.
    """
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT id FROM documents WHERE source=? AND source_id=?",
            (doc["source"], str(doc["source_id"])),
        )
        row = cur.fetchone()
        if row:
            return row["id"], False
        cur = conn.execute(
            """INSERT INTO documents
               (source, source_id, url, title, raw_text, published_date, fetched_at, lang)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                doc["source"],
                str(doc["source_id"]),
                doc.get("url"),
                doc.get("title"),
                doc.get("raw_text"),
                doc.get("published_date"),
                now_iso(),
                doc.get("lang", "en"),
            ),
        )
        return cur.lastrowid, True


def documents_missing_extractor(extractor: str):
    """Documents that have no extraction yet for the given extractor name."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT d.* FROM documents d
               WHERE NOT EXISTS (
                   SELECT 1 FROM extractions e
                   WHERE e.document_id = d.id AND e.extractor = ?
               )""",
            (extractor,),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Extractions
# ---------------------------------------------------------------------------
def save_extraction(document_id: int, extractor: str, model_version: str,
                    prompt_version: str, result: dict, raw_output: str = "",
                    make_active: bool = True):
    payload = {f: json.dumps(result.get(f, []), ensure_ascii=False) for f in JSON_FIELDS}
    with get_conn() as conn:
        if make_active:
            conn.execute(
                "UPDATE extractions SET is_active=0 WHERE document_id=?",
                (document_id,),
            )
        conn.execute(
            """INSERT OR REPLACE INTO extractions
               (document_id, extractor, model_version, prompt_version, created_at,
                summary, event_type, study_type,
                countries, regions, pathogens, diseases, antibiotics,
                resistance_genes, keywords, raw_output, is_active)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                document_id, extractor, model_version, prompt_version, now_iso(),
                result.get("summary", ""),
                result.get("event_type", ""),
                result.get("study_type", ""),
                payload["countries"], payload["regions"], payload["pathogens"],
                payload["diseases"], payload["antibiotics"],
                payload["resistance_genes"], payload["keywords"],
                raw_output, 1 if make_active else 0,
            ),
        )


def get_active_extraction(document_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM extractions WHERE document_id=? AND is_active=1 LIMIT 1",
            (document_id,),
        ).fetchone()
        return dict(row) if row else None


# ---------------------------------------------------------------------------
# Entities & relations (rebuilt from the active extraction of each doc)
# ---------------------------------------------------------------------------
ENTITY_MAP = [
    ("pathogens", "pathogen"),
    ("countries", "country"),
    ("regions", "region"),
    ("antibiotics", "antibiotic"),
    ("resistance_genes", "resistance_gene"),
    ("diseases", "disease"),
]


def rebuild_graph_for_document(document_id: int):
    """(Re)build entities + relations for one document from its active extraction."""
    ext = get_active_extraction(document_id)
    with get_conn() as conn:
        conn.execute("DELETE FROM entities WHERE document_id=?", (document_id,))
        conn.execute("DELETE FROM relations WHERE document_id=?", (document_id,))
        if not ext:
            return

        buckets = {}
        for field, etype in ENTITY_MAP:
            values = json.loads(ext.get(field) or "[]")
            buckets[etype] = values
            for v in values:
                conn.execute(
                    "INSERT INTO entities (document_id, entity_type, value) VALUES (?,?,?)",
                    (document_id, etype, v),
                )
        if ext.get("event_type"):
            conn.execute(
                "INSERT INTO entities (document_id, entity_type, value) VALUES (?,?,?)",
                (document_id, "event_type", ext["event_type"]),
            )

        # Knowledge-graph edges = pathogen co-occurring with everything else in
        # the same document (Pathogen -> Country / Gene / Antibiotic / ...).
        pathogens = buckets.get("pathogen", [])
        for p in pathogens:
            for etype in ("country", "resistance_gene", "antibiotic", "disease", "region"):
                for v in buckets.get(etype, []):
                    conn.execute(
                        """INSERT INTO relations
                           (document_id, src_type, src_value, dst_type, dst_value)
                           VALUES (?,?,?,?,?)""",
                        (document_id, "pathogen", p, etype, v),
                    )


def log_run(started_at: str, summary: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO run_log (started_at, finished_at, summary) VALUES (?,?,?)",
            (started_at, now_iso(), summary),
        )


if __name__ == "__main__":
    init_db()
    print(f"Initialised database at {config.DB_PATH}")
