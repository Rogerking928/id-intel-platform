"""
Central configuration for the ID-Intel platform.

Everything you might want to tweak (which pathogens to track, how many
articles to pull per day, which model to use) lives here so you never have to
dig through the code.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _load_dotenv():
    """Tiny, dependency-free .env loader.

    If a `.env` file sits next to this config, read KEY=VALUE lines into the
    environment (without overwriting anything already set in the real env).
    This means: paste your key into .env and just run `python run_daily.py` —
    no `source .env` dance needed.
    """
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
DB_PATH = DATA_DIR / "id_intel.db"

DATA_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Politeness / networking
# ---------------------------------------------------------------------------
# A contact email is required by NCBI etiquette and generally good manners.
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "wangyenjen0301@gmail.com")
USER_AGENT = f"ID-Intel-Platform/0.1 (mailto:{CONTACT_EMAIL})"
HTTP_TIMEOUT = 30  # seconds

# Optional NCBI API key raises PubMed rate limit from 3 to 10 req/s.
NCBI_API_KEY = os.getenv("NCBI_API_KEY", "").strip()

# ---------------------------------------------------------------------------
# AI extraction backend
# ---------------------------------------------------------------------------
# The platform ALWAYS runs the free, offline rule-based extractor.
# If you set GEMINI_API_KEY (free tier, no credit card), it will ALSO run a
# Gemini extraction so you can compare the two for Paper 1.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
# Free-tier friendliness: cap how many docs get an LLM extraction per run, and
# space calls out so we stay under the requests-per-minute limit (avoids 429s).
# Raise GEMINI_MAX_PER_RUN once you're on a paid tier; 0 = no cap.
GEMINI_MAX_PER_RUN = int(os.getenv("GEMINI_MAX_PER_RUN", "50"))
GEMINI_MIN_INTERVAL = float(os.getenv("GEMINI_MIN_INTERVAL", "4.5"))  # seconds/call

# Extractor identifiers stored with every extraction (audit trail for the paper)
RULE_EXTRACTOR_NAME = "rule_based"
RULE_EXTRACTOR_VERSION = "v1"
PROMPT_VERSION = "v1"

# ---------------------------------------------------------------------------
# How much to collect per daily run (keep modest so runs stay fast)
# ---------------------------------------------------------------------------
PUBMED_MAX_PER_QUERY = int(os.getenv("PUBMED_MAX_PER_QUERY", "40"))
PUBMED_LOOKBACK_DAYS = int(os.getenv("PUBMED_LOOKBACK_DAYS", "30"))
CT_MAX_STUDIES = int(os.getenv("CT_MAX_STUDIES", "40"))
WHO_MAX_ITEMS = int(os.getenv("WHO_MAX_ITEMS", "30"))

# ---------------------------------------------------------------------------
# PubMed search queries. Each becomes a separate esearch call.
# Focused on the flagship pathogens (CRE / VRE / MRSA) + broader AMR.
# ---------------------------------------------------------------------------
PUBMED_QUERIES = [
    "carbapenem-resistant Enterobacterales",
    "vancomycin-resistant enterococcus",
    "methicillin-resistant Staphylococcus aureus",
    "carbapenem-resistant Acinetobacter baumannii",
    "Candida auris",
    "antimicrobial resistance surveillance",
    "NDM OR KPC OR OXA-48 carbapenemase",
]

# ClinicalTrials.gov search terms
CT_QUERIES = [
    "carbapenem resistant",
    "vancomycin resistant enterococcus",
    "MRSA infection",
    "multidrug resistant infection",
    "cefiderocol",
]

# ---------------------------------------------------------------------------
# WHO Disease Outbreak News JSON (OData) API
# ---------------------------------------------------------------------------
WHO_DON_API = "https://www.who.int/api/news/diseaseoutbreaknews"
WHO_DON_ITEM_URL = "https://www.who.int/emergencies/disease-outbreak-news/item/"

# ---------------------------------------------------------------------------
# RSS feeds (CDC + ECDC). If a URL dies, the collector skips it gracefully.
# ---------------------------------------------------------------------------
CDC_FEEDS = [
    # CDC MMWR (Morbidity and Mortality Weekly Report)
    "https://tools.cdc.gov/api/v2/resources/media/403372.rss",
    # CDC Newsroom
    "https://tools.cdc.gov/api/v2/resources/media/132608.rss",
]

ECDC_FEEDS = [
    # ECDC news / communicable disease threats
    "https://www.ecdc.europa.eu/en/taxonomy/term/2942/feed",
]

# Regions used for the "which regions are lighting up" analysis.
# APAC is emphasised because it is the focus of the research programme.
DEFAULT_REGION = "Other"
