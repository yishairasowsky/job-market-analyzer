# Configuration for the Job Market Analyzer
# Edit this file to personalize the tool for your background and preferences

# ---------------------------------------------------------------------------
# WHO YOU ARE — used by the report writer to give personalized advice
# ---------------------------------------------------------------------------

MY_BACKGROUND = """
American data scientist and AI developer living in Israel (Beitar Illit, near Jerusalem).
Looking for fully remote work, ideally with US companies. Open to Israeli companies and
some European companies as long as the role is truly remote (not "remote in Germany only").
Available to work US or European hours. Not eligible for EU work authorization.

Recent experience: data science role at a startup (LoopHQ), math research for an educational
organization (extracting mathematical content from Talmudic texts), building AI-powered tools
including a Gmail smart-compose extension and a multi-agent job market analyzer.

Comfortable with Python, Claude API / Anthropic SDK, data science workflows, and building
AI agent pipelines. Learning agent orchestration and semantic layer architecture.
"""

MY_SKILLS = [
    "Python",
    "Claude API / Anthropic SDK",
    "data science",
    "machine learning",
    "LLM pipelines",
    "agent orchestration",
    "data analysis",
    "SQL",
    "Git",
]

# ---------------------------------------------------------------------------
# WHAT ROLES TO SEARCH FOR
# ---------------------------------------------------------------------------

TARGET_ROLES = [
    "data scientist",
    "ai engineer",
    "machine learning engineer",
    "data engineer",
    "llm engineer",
    "ai developer",
    "ml engineer",
    "ai researcher",
]

# Keywords that broaden the search beyond exact title matches
KEYWORDS = [
    "python",
    "machine learning",
    "llm",
    "langchain",
    "data science",
    "artificial intelligence",
    "agent",
    "openai",
    "anthropic",
    "rag",
    "generative ai",
]

# ---------------------------------------------------------------------------
# LOCATION PREFERENCES
# ---------------------------------------------------------------------------

# Jobs containing these phrases are skipped — they are not accessible to you
EXCLUDED_LOCATION_PHRASES = [
    "remote in de",
    "remote in germany",
    "remote in eu only",
    "must be based in germany",
    "must be based in europe",
    "eu work authorization required",
    "eu citizens only",
]

# ---------------------------------------------------------------------------
# LIMITS
# ---------------------------------------------------------------------------

# How many job postings to collect in total
MAX_JOBS = 60

# How many companies to run web-search funding checks on
# (Each check = one Claude API call, so keep this reasonable)
MAX_COMPANIES_TO_CHECK = 20

# How many recent HN hiring threads to pull from (1 = current month only)
HN_THREADS_TO_FETCH = 2

# Claude model to use for all agents
MODEL = "claude-sonnet-4-6"
