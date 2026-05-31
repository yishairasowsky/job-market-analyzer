"""
Agent 2 — Funding Detector

For each company found by the Job Collector, this agent searches the web
for recent funding news (2024-2026). It uses DuckDuckGo search to find
relevant news snippets, then asks Claude to interpret whether the company
recently raised money and how much.

Companies that recently received funding are high-priority targets because
they have money and are in growth mode — meaning they are more likely to hire.
"""

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


def detect_funding(companies):
    if not DDGS_AVAILABLE:
        print("Agent 2 (Funding Detector): Skipping — duckduckgo-search not installed.")
        print("  Run: pip install duckduckgo-search")
        return []

    print(f"Agent 2 (Funding Detector): Checking {min(len(companies), MAX_COMPANIES_TO_CHECK)} companies for recent funding...")

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    funded = []

    for company in companies[:MAX_COMPANIES_TO_CHECK]:
        if not company:
            continue

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

Search results about this company:
{search_text}

Reply with ONLY one of these formats:
YES: [round and amount if known, e.g. "Series A, $12M, March 2025"]
NO
UNCLEAR"""
                }]
            )

            answer = response.content[0].text.strip()
            if answer.upper().startswith("YES"):
                detail = answer[4:].strip() if len(answer) > 4 else "recently funded"
                funded.append({"company": company, "funding": detail})
                print(f"  Funded: {company} — {detail}")

        except Exception as e:
            print(f"  Could not check {company}: {e}")
            continue

    print(f"  Found {len(funded)} recently funded companies.")
    return funded


def _search_funding_news(company):
    """Search DuckDuckGo for funding news about a company."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(
                f'"{company}" funding raised million 2024 OR 2025 OR 2026 startup',
                max_results=3
            ))
        return "\n".join([r.get("body", "") for r in results if r.get("body")])
    except Exception:
        return ""
