"""
Agent 5 — Outreach Writer

For each priority company (funded startups first, then top job matches),
researches what the company does and generates a personalized cold email or
LinkedIn message ready to send.

Output is a plain-text file saved to outreach/outreach_YYYY-MM-DD.txt.
"""

import anthropic
import os
import sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import MODEL, MY_BACKGROUND, MY_SKILLS

try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        DDGS_AVAILABLE = True
    except ImportError:
        DDGS_AVAILABLE = False

# Max companies to write outreach for — each one is one Claude call
MAX_OUTREACH_TARGETS = 5


def write_outreach(jobs, funded_companies):
    """Generate personalized outreach messages for top target companies.

    Prioritizes funded companies, then fills remaining slots from the top job
    matches. Returns a formatted string ready to save as a text file.
    """
    print(f"Agent 5 (Outreach Writer): Writing personalized outreach messages...")

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    my_skills_text = ", ".join(MY_SKILLS)
    today = date.today().strftime("%B %d, %Y")

    # Build the ordered target list: funded companies first, then top jobs
    targets = []
    seen_companies = set()

    for fc in funded_companies:
        company_name = fc["company"]
        if company_name in seen_companies:
            continue
        # Find the matching job record so we have role + URL
        job = _find_job(jobs, company_name)
        targets.append({
            "company": company_name,
            "funding": fc["funding"],
            "role": job.get("title", "AI/Data role") if job else "AI/Data role",
            "url": job.get("url", "") if job else "",
            "description": job.get("description", "") if job else "",
        })
        seen_companies.add(company_name)

    # Fill remaining slots from top jobs (not already in targets)
    for job in jobs:
        if len(targets) >= MAX_OUTREACH_TARGETS:
            break
        company = job.get("company", "")
        if not company or company in seen_companies:
            continue
        targets.append({
            "company": company,
            "funding": None,
            "role": job.get("title", ""),
            "url": job.get("url", ""),
            "description": job.get("description", ""),
        })
        seen_companies.add(company)

    if not targets:
        print("  No targets found.")
        return ""

    messages = []

    for i, target in enumerate(targets, 1):
        company = target["company"]
        print(f"  [{i}/{len(targets)}] Writing outreach for {company}...")

        # Research what the company actually does
        company_context = _research_company(company, target["description"])

        # Ask Claude to write the message
        funding_note = f"They recently received funding ({target['funding']})." if target["funding"] else ""

        prompt = f"""Today is {today}. You are writing a short, personalized cold outreach message on behalf of a job seeker.

ABOUT THE SENDER:
{MY_BACKGROUND}

SENDER'S SKILLS: {my_skills_text}

TARGET COMPANY: {company}
ROLE THEY ARE HIRING FOR: {target['role']}
{funding_note}

WHAT YOU KNOW ABOUT THIS COMPANY:
{company_context if company_context else "A tech startup hiring for AI/data roles."}

---

Write TWO short outreach messages. Both should be specific to this company — mention something real about what they do. Do not be generic.

MESSAGE 1 — LinkedIn connection request (under 300 characters, plain text, no line breaks):
A brief, punchy note to send with a LinkedIn connection request to their hiring manager or CEO.

MESSAGE 2 — Cold email (5-7 sentences, plain text):
Subject line on its own line, then the body. Open with something specific about the company, explain who you are and why you're a fit, and close with a clear ask (a 20-minute call).

Write both messages in first person as if you are the sender. Be direct and confident, not salesy. No emojis."""

        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}]
            )
            message_text = response.content[0].text.strip()
        except Exception as e:
            print(f"    Error generating message for {company}: {e}")
            message_text = "[Error generating message]"

        # Format the block for this company
        block = _format_block(target, message_text)
        messages.append(block)

    print(f"  Done. Wrote {len(messages)} outreach messages.")

    separator = "\n" + "=" * 60 + "\n"
    header = f"OUTREACH MESSAGES — {today}\n{'=' * 60}\n\n"
    return header + separator.join(messages)


def _find_job(jobs, company_name):
    """Return the first job record matching this company name."""
    for job in jobs:
        if job.get("company", "").lower() == company_name.lower():
            return job
    return None


def _research_company(company_name, job_description):
    """Get a brief summary of what the company does using DuckDuckGo."""
    if not DDGS_AVAILABLE:
        return job_description[:300] if job_description else ""

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(
                f'"{company_name}" company what they do product',
                max_results=2
            ))
        snippets = [r.get("body", "") for r in results if r.get("body")]
        web_context = " ".join(snippets)[:400]
        # Combine web results with the job description for richer context
        combined = web_context
        if job_description:
            combined += "\n\nFrom their job posting: " + job_description[:300]
        return combined[:700]
    except Exception:
        return job_description[:300] if job_description else ""


def _format_block(target, message_text):
    """Format one company's outreach block."""
    lines = []
    lines.append(f"COMPANY: {target['company']}")
    lines.append(f"ROLE:    {target['role']}")
    if target["url"]:
        lines.append(f"URL:     {target['url']}")
    if target["funding"]:
        lines.append(f"FUNDED:  {target['funding']}")
    lines.append("")
    lines.append(message_text)
    lines.append("")
    return "\n".join(lines)
