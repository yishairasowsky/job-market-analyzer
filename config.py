# Configuration for the Job Market Analyzer
# Edit these to customize what roles and skills you are targeting

TARGET_ROLES = [
    "data scientist",
    "ai engineer",
    "machine learning engineer",
    "data engineer",
    "llm engineer",
    "ai developer",
    "ml engineer",
]

# These keywords broaden the search to catch relevant postings
# even if the job title is not an exact match
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
]

# How many job postings to collect in total
MAX_JOBS = 50

# How many companies to check for recent funding news
# (Each check makes a web search + one Claude call, so keep this reasonable)
MAX_COMPANIES_TO_CHECK = 15

# Claude model to use for all agents
MODEL = "claude-sonnet-4-6"
