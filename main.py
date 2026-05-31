"""
Job Market Analyzer — Main Orchestrator

This script coordinates five AI agents to produce a weekly job market report
and ready-to-send outreach messages:

  Agent 1 (Job Collector)    — Fetches relevant job postings from public job boards
  Agent 2 (Funding Detector) — Identifies which companies recently received funding
  Agent 3 (Skills Analyzer)  — Extracts in-demand skills and role trends from postings
  Agent 4 (Report Writer)    — Synthesizes everything into an actionable weekly report
  Agent 5 (Outreach Writer)  — Writes personalized cold emails and LinkedIn messages
                               for each top target company

Run with:
  python main.py
"""

import os
import sys
from pathlib import Path
from datetime import date

# Windows terminals often can't display Unicode emoji — this fixes that
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv()

from agents.job_collector import collect_jobs
from agents.funding_detector import detect_funding
from agents.skills_analyzer import analyze_skills
from agents.report_writer import write_report
from agents.outreach_writer import write_outreach


def main():
    print("\nJOB MARKET ANALYZER")
    print("=" * 40)

    # Check that the API key is available before doing anything
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\nERROR: ANTHROPIC_API_KEY is not set.")
        print("Add it to a .env file in this directory:")
        print("  ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    # --- Agent 1: Collect job postings ---
    jobs = collect_jobs()
    if not jobs:
        print("\nNo relevant jobs found. Check your internet connection.")
        sys.exit(1)

    # --- Agent 2: Detect funding ---
    # Pass full job list so the detector can read descriptions for explicit
    # funding mentions (common in HN posts) before falling back to web search
    funded_companies = detect_funding(jobs)

    # --- Agent 3: Analyze skills across all postings ---
    skills_summary = analyze_skills(jobs)

    # --- Agent 4: Write the final report ---
    report = write_report(jobs, funded_companies, skills_summary)

    # Save the report to the reports/ folder
    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    report_path = reports_dir / f"report_{date.today()}.txt"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    # Print to terminal as well
    print("\n" + "=" * 50)
    print(report)
    print("=" * 50)
    print(f"\nReport saved to: {report_path}")

    # --- Agent 5: Write personalized outreach messages ---
    outreach = write_outreach(jobs, funded_companies)

    if outreach:
        outreach_dir = Path(__file__).parent / "outreach"
        outreach_dir.mkdir(exist_ok=True)
        outreach_path = outreach_dir / f"outreach_{date.today()}.txt"

        with open(outreach_path, "w", encoding="utf-8") as f:
            f.write(outreach)

        print(f"Outreach saved to: {outreach_path}")
    else:
        print("No outreach messages generated.")


if __name__ == "__main__":
    main()
