"""
Agent 3 — Skills Analyzer

Reads all the job postings collected by the Job Collector and asks Claude
to extract patterns: which technical skills appear most, what kind of roles
are in demand, and what trends are visible this week.
"""

import anthropic
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import MODEL, MY_SKILLS


def analyze_skills(jobs, user_skills=None, on_progress=None):
    def progress(msg):
        print(msg)
        if on_progress:
            on_progress(msg)

    if not jobs:
        return "No jobs available to analyze."

    skills = user_skills if user_skills is not None else MY_SKILLS

    progress(f"Agent 3 (Skills Analyzer): Analyzing skills across {len(jobs)} postings...")

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    job_blocks = []
    for job in jobs[:25]:
        tags = ", ".join(job.get("tags", [])) or "none listed"
        block = (
            f"Title: {job['title']}\n"
            f"Company: {job['company']}\n"
            f"Tags: {tags}\n"
            f"Description: {job['description'][:400]}"
        )
        job_blocks.append(block)

    job_text = "\n---\n".join(job_blocks)

    response = client.messages.create(
        model=MODEL,
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"""Analyze these job postings for a candidate with these skills: {", ".join(skills)}.

Extract the following:

1. TOP 10 TECHNICAL SKILLS — specific tools, languages, and frameworks mentioned most often
2. TOP 5 ROLE FOCUSES — types of work most commonly described
3. SKILLS GAP — which of the top 10 skills does the candidate NOT already have?
4. ONE TREND — any notable pattern across these postings

Job postings:
{job_text}

Be specific and concise. Plain text only."""
        }]
    )

    result = response.content[0].text
    progress("  Skills analysis complete.")
    return result
