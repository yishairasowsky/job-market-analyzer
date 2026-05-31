"""
Agent 4 — Report Writer

Takes the outputs from all three previous agents and produces a clean,
readable weekly report personalized to the user's background and skills.
"""

import anthropic
import os
import sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import MODEL, MY_BACKGROUND, MY_SKILLS


def write_report(jobs, funded_companies, skills_summary, user_background=None, user_skills=None, on_progress=None):
    def progress(msg):
        print(msg)
        if on_progress:
            on_progress(msg)

    progress("Agent 4 (Report Writer): Writing your weekly report...")

    background = user_background if user_background else MY_BACKGROUND
    skills = user_skills if user_skills is not None else MY_SKILLS

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    today = date.today().strftime("%B %d, %Y")

    funded_text = "\n".join([
        f"- {f['company']}: {f['funding']}" for f in funded_companies
    ]) if funded_companies else "None identified this week."

    top_jobs_text = "\n".join([
        f"- {job['title']} at {job['company']} ({job['location']}) | {job['url']}"
        for job in jobs[:15]
    ])

    my_skills_text = ", ".join(skills)

    response = client.messages.create(
        model=MODEL,
        max_tokens=900,
        messages=[{
            "role": "user",
            "content": f"""Today's date is {today}. Write a weekly job market report for the following person:

ABOUT THE READER:
{background}

THEIR SKILLS: {my_skills_text}

---

THIS WEEK'S DATA:

Recently funded companies (priority targets — they have money and are actively hiring):
{funded_text}

Job postings found this week:
{top_jobs_text}

Market skills analysis:
{skills_summary}

---

Write the report with exactly these four sections. Use plain text, no markdown.
Today's date is {today} — use this exact date, do not invent a different date.

HIGHLIGHTS
2-3 sentences on what stands out this week specifically for this reader.

PRIORITY COMPANIES TO APPLY TO
If there are funded companies with relevant roles, list them first.
Then list the top 2-3 open roles that best match the reader's skills.
Include the URL for each role.

IN-DEMAND SKILLS THIS WEEK
Quick list of the top skills appearing in postings.
Flag which ones the reader already has vs. which are gaps.

RECOMMENDED ACTIONS
3 specific, actionable things to do THIS week.
Be direct and concrete — not generic advice.

Keep total under 400 words."""
        }]
    )

    header = (
        f"JOB MARKET REPORT — {today}\n"
        f"{'=' * 50}\n\n"
    )

    progress("  Report complete.")
    return header + response.content[0].text
