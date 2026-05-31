"""
Agent 4 — Report Writer

Takes the outputs from all three previous agents and produces a clean,
readable weekly report. This is the final synthesis step — turning data
into a decision-making tool you can actually act on.
"""

import anthropic
import os
import sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import MODEL


def write_report(jobs, funded_companies, skills_summary):
    print("Agent 4 (Report Writer): Writing your weekly report...")

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Format the funded companies section
    if funded_companies:
        funded_text = "\n".join([
            f"- {f['company']}: {f['funding']}" for f in funded_companies
        ])
    else:
        funded_text = "None identified this week."

    # List the top job postings
    top_jobs_text = "\n".join([
        f"- {job['title']} at {job['company']} | {job['url']}"
        for job in jobs[:12]
    ])

    response = client.messages.create(
        model=MODEL,
        max_tokens=700,
        messages=[{
            "role": "user",
            "content": f"""Write a concise weekly job market report. The reader is a data scientist and AI developer in Israel who prefers remote work and is actively job hunting.

INPUT DATA:

Recently funded companies (these are priority targets — they have money and are hiring):
{funded_text}

Top job postings found this week:
{top_jobs_text}

Skills analysis:
{skills_summary}

Write the report with exactly these sections:

HIGHLIGHTS
[2-3 sentences summarizing what stands out this week]

PRIORITY COMPANIES TO APPLY TO
[List funded companies that have open roles, or top companies if none funded]

IN-DEMAND SKILLS THIS WEEK
[The top skills from the analysis, formatted as a quick-read list]

RECOMMENDED ACTIONS
[3 specific things the reader should do this week based on this data]

Keep the total under 350 words. Friendly but professional tone."""
        }]
    )

    header = (
        f"JOB MARKET REPORT\n"
        f"Week of {date.today().strftime('%B %d, %Y')}\n"
        f"{'=' * 50}\n\n"
    )

    print("  Report complete.")
    return header + response.content[0].text
