"""
Job Market Analyzer — Main Orchestrator

This script coordinates four AI agents to produce a weekly job market report:

  Agent 1 (Job Collector)    — Fetches relevant job postings from public job boards
  Agent 2 (Funding Detector) — Identifies which companies recently received funding
  Agent 3 (Skills Analyzer)  — Extracts in-demand skills and role trends from postings
  Agent 4 (Report Writer)    — Synthesizes everything into an actionable weekly report

Run with:
  python main.py
"""

import os
import sys
from pathlib import Path
from datetime import date

from dotenv import load_dotenv
load_dotenv()

from agents.job_collector import collect_jobs
from agents.funding_detector import detect_funding
from agents.skills_analyzer import analyze_skills
from agents.report_writer import write_report


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

    # --- Agent 2: Detect funding for the companies found ---
    companies = list({job["company"] for job in jobs if job.get("company")})
    funded_companies = detect_funding(companies)

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
    print(f"\nSaved to: {report_path}")


if __name__ == "__main__":
    main()
