"""
Agent 3 — Skills Analyzer

Reads all the job postings collected by the Job Collector and asks Claude
to extract patterns: which technical skills appear most, what kind of roles
are in demand, and what trends are visible this week.

This is the "intelligence" layer — turning raw job text into actionable
information about what the market actually wants right now.
"""

import anthropic
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import MODEL


def analyze_skills(jobs):
    if not jobs:
        return "No jobs available to analyze."

    print(f"Agent 3 (Skills Analyzer): Analyzing skills across {len(jobs)} postings...")

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Build a readable summary of the jobs (limit tokens by capping descriptions)
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
            "content": f"""Analyze these job postings and extract the following:

1. TOP 10 TECHNICAL SKILLS — the specific tools, languages, and frameworks mentioned most (e.g. Python, LangChain, dbt, Spark, etc.)
2. TOP 5 ROLE FOCUSES — the types of work most commonly described (e.g. "LLM fine-tuning", "building data pipelines", "RAG systems", etc.)
3. ONE TREND — any notable pattern you see across these postings

Job postings:
{job_text}

Be specific and concise. Plain text only."""
        }]
    )

    result = response.content[0].text
    print("  Skills analysis complete.")
    return result
