"""
Extraction pipeline.

For every document that has not yet been processed by a given extractor:
  1. run the rule-based extractor (always),
  2. run the Gemini extractor too if a key is configured,
  3. store both (with full audit metadata),
  4. pick the "active" extraction that feeds search + graph
     (Gemini if available, else rule-based),
  5. rebuild that document's entities and knowledge-graph relations.
"""
import config
import db
from extract import rule_based, llm


def run(verbose: bool = True) -> dict:
    stats = {"rule_based": 0, "llm": 0, "llm_errors": 0, "graph": 0}
    use_llm = llm.is_available()
    touched = set()  # doc ids whose active extraction changed -> rebuild only these

    # --- rule-based pass (baseline, always) ---
    for doc in db.documents_missing_extractor(config.RULE_EXTRACTOR_NAME):
        result = rule_based.extract(doc["title"] or "", doc["raw_text"] or "", doc["source"])
        # rule-based is "active" only if we won't also run the LLM
        db.save_extraction(
            doc["id"], config.RULE_EXTRACTOR_NAME, config.RULE_EXTRACTOR_VERSION,
            config.PROMPT_VERSION, result, raw_output="", make_active=not use_llm,
        )
        touched.add(doc["id"])
        stats["rule_based"] += 1

    # --- LLM pass (optional, becomes the active extraction) ---
    # Capped per run and paced so free-tier rate limits aren't exceeded. Run
    # `run_daily.py` on subsequent days (or raise GEMINI_MAX_PER_RUN) to work
    # through the backlog.
    if use_llm:
        import time
        pending = db.documents_missing_extractor(llm.name())
        cap = config.GEMINI_MAX_PER_RUN or len(pending)
        todo = pending[:cap]
        if verbose and len(pending) > len(todo):
            print(f"  [LLM] {len(pending)} docs pending; processing {len(todo)} "
                  f"this run (GEMINI_MAX_PER_RUN={config.GEMINI_MAX_PER_RUN}).")
        consec_rate_limit = 0
        for i, doc in enumerate(todo):
            try:
                result, raw = llm.extract(doc["title"] or "", doc["raw_text"] or "", doc["source"])
                db.save_extraction(
                    doc["id"], llm.name(), llm.name(), config.PROMPT_VERSION,
                    result, raw_output=raw, make_active=True,
                )
                touched.add(doc["id"])
                stats["llm"] += 1
                consec_rate_limit = 0
            except Exception as exc:  # noqa: BLE001
                stats["llm_errors"] += 1
                if verbose:
                    from analysis.trends import redact_secrets
                    print(f"  [LLM] doc {doc['id']} failed: {redact_secrets(str(exc))}")
                # If the free-tier quota is exhausted, stop instead of grinding
                # through every remaining doc with slow back-off. Resumes next run.
                if "429" in str(exc) or "Too Many Requests" in str(exc):
                    consec_rate_limit += 1
                    if consec_rate_limit >= 3:
                        print("  [LLM] repeated rate-limit — stopping LLM pass "
                              "for this run; remaining docs resume next run.")
                        break
            if i < len(todo) - 1 and config.GEMINI_MIN_INTERVAL > 0:
                time.sleep(config.GEMINI_MIN_INTERVAL)

    # --- rebuild graph ONLY for documents changed this run ---
    # (First run: every new doc is "touched", so the whole graph builds. Later
    #  runs touch only new/re-extracted docs, so this stays fast.)
    for doc_id in touched:
        db.rebuild_graph_for_document(doc_id)
        stats["graph"] += 1

    if verbose:
        print(f"  extraction: rule_based={stats['rule_based']} "
              f"llm={stats['llm']} (errors={stats['llm_errors']}) "
              f"graph_rebuilt={stats['graph']}")
    return stats
