"""Generate the auditable external-validation bundle for VIGIL Paper 2."""
from analysis.surveillance_validation import write_research_bundle


if __name__ == "__main__":
    print(f"Wrote research bundle: {write_research_bundle()}")
