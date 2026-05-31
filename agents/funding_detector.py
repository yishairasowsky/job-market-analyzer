"""
Agent 2 — Funding Detector

Two strategies for finding funded companies:

Strategy A (fast, no API call needed): Scan the job description itself for funding
mentions. HN posts in particular often say things like "we raised a $10M Series A"
or "backed by Y Combinator" right in the text.

Strategy B (web search): For companies without an explicit funding mention in their
post, search DuckDuckGo for recent funding news and ask Claude to interpret results.

HN-sourced jobs are checked first since they are the most likely to be funded.
"""

import re
import anthropic
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import MAX_COMPANIES_TO_CHECK, MODEL

try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        DDGS_AVAILABLE = True
    except ImportError:
        DDGS_AVAILABLE = False

FUNDING_PATTERNS = [
    r'series [abcde]',
    r'seed (round|funding|stage)',
    r'raised \$[\d\.]+[mb]',
    r'y combinator|yc [ws]\d+',
    r'\$[\d\.]+[mb] (round|funding|raised)',
    r'backed by (a16z|sequoia|benchmark|andreessen|greylock|accel|lightspeed)',
    r'venture.backed',
    r'we.re funded',
]


def detect_funding(jobs, on_progress=None):
    def progress(msg):
        print(msg)
        if on_progress:
            on_progress(msg)

    progress(f"Agent 2 (Funding Detector): Checking companies for recent funding...")

    funded = []
    already_found = set()

    # Strategy A: scan job descriptions for explicit funding mentions
    for job in jobs:
        company = job.get("company", "")
        if not company or company in already_found:
            continue
        description = job.get("description", "")
        funding_detail = _extract_funding_from_text(description)
        if funding_detail:
            funded.append({"company": company, "funding": funding_detail})
            already_found.add(company)
            progress(f"  Funded (from post): {company} — {funding_detail}")

    # Strategy B: web search for remaining companies
    if not DDGS_AVAILABLE:
        progress("  Skipping web search — ddgs not installed. Run: pip install ddgs")
    else:
        hn_companies = [j["company"] for j in jobs if "hn_hiring" in j.get("source", "") and j["company"] not in already_found]
        other_companies = [j["company"] for j in jobs if "hn_hiring" not in j.get("source", "") and j["company"] not in already_found]
        companies_to_check = (hn_companies + other_companies)[:MAX_COMPANIES_TO_CHECK]

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        for company in companies_to_check:
            if not company:
                continue
            progress(f"  Checking {company}...")
            search_text = _search_funding_news(company)
            if not search_text:
                continue
            try:
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=150,
                    messages=[{
                        "role": "user",
                        "content": f"""Did the company "{company}" receive investment funding in 2024, 2025, or 2026?

Search results:
{search_text}

Reply with ONLY one of:
YES: [round and amount if known, e.g. "Series A, $12M, March 2025"]
NO
UNCLEAR"""
                    }]
                )
                answer = response.content[0].text.strip()
                if answer.upper().startswith("YES"):
                    detail = answer[4:].strip() if len(answer) > 4 else "recently funded"
                    funded.append({"company": company, "funding": detail})
                    already_found.add(company)
                    progress(f"  Funded (web search): {company} — {detail}")
            except Exception as e:
                progress(f"  Could not check {company}: {e}")

    progress(f"  Found {len(funded)} recently funded companies.")
    return funded


def _extract_funding_from_text(text):
    text_lower = text.lower()
    for pattern in FUNDING_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 60)
            return text[start:end].strip().split("\n")[0][:120]
    return None


def _search_funding_news(company):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(
                f'"{company}" funding raised million 2024 OR 2025 OR 2026 startup',
                max_results=3
            ))
        return "\n".join([r.get("body", "") for r in results if r.get("body")])
    except Exception:
        return ""
