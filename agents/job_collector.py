"""
Agent 1 — Job Collector

Fetches job postings from two free APIs (no API keys required):
  - Arbeitnow: strong coverage of European remote roles
  - Remotive: strong coverage of US remote roles

Filters both sources for data science and AI engineering roles.
Returns a combined, deduplicated list of structured job dicts.
"""

import requests
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import TARGET_ROLES, KEYWORDS, MAX_JOBS

ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"
REMOTIVE_URL = "https://remotive.com/api/remote-jobs"
REMOTIVE_CATEGORIES = ["data", "software-dev", "product"]


def collect_jobs():
    print("Agent 1 (Job Collector): Fetching job postings...")

    all_raw = []
    all_raw += _fetch_arbeitnow()
    all_raw += _fetch_remotive()

    # Deduplicate by (title, company)
    seen = set()
    relevant = []
    for job in all_raw:
        key = (job["title"], job["company"])
        if key in seen:
            continue
        seen.add(key)
        relevant.append(job)
        if len(relevant) >= MAX_JOBS:
            break

    print(f"  Found {len(relevant)} relevant job postings ({len([j for j in relevant if j.get('source') == 'remotive'])} US-remote, {len([j for j in relevant if j.get('source') == 'arbeitnow'])} European).")
    return relevant


def _fetch_arbeitnow():
    try:
        response = requests.get(ARBEITNOW_URL, timeout=15)
        response.raise_for_status()
        jobs = response.json().get("data", [])
    except Exception as e:
        print(f"  Warning: Arbeitnow unavailable — {e}")
        return []

    results = []
    for job in jobs:
        if not _is_relevant(job.get("title", ""), job.get("description", ""), job.get("tags", [])):
            continue
        results.append({
            "title": job.get("title"),
            "company": job.get("company_name"),
            "location": job.get("location", "Remote"),
            "remote": job.get("remote", False),
            "url": job.get("url"),
            "description": job.get("description", "")[:800],
            "tags": job.get("tags", []),
            "posted": job.get("created_at"),
            "source": "arbeitnow",
        })
    return results


def _fetch_remotive():
    results = []
    for category in REMOTIVE_CATEGORIES:
        try:
            response = requests.get(
                REMOTIVE_URL,
                params={"category": category, "limit": 50},
                timeout=15
            )
            response.raise_for_status()
            jobs = response.json().get("jobs", [])
        except Exception as e:
            print(f"  Warning: Remotive ({category}) unavailable — {e}")
            continue

        for job in jobs:
            if not _is_relevant(job.get("title", ""), job.get("description", ""), job.get("tags", [])):
                continue
            results.append({
                "title": job.get("title"),
                "company": job.get("company_name"),
                "location": job.get("candidate_required_location", "Remote"),
                "remote": True,
                "url": job.get("url"),
                "description": job.get("description", "")[:800],
                "tags": job.get("tags", []) if isinstance(job.get("tags"), list) else [],
                "posted": job.get("publication_date"),
                "source": "remotive",
            })
    return results


def _is_relevant(title, description, tags):
    title = title.lower()
    description = description.lower()
    tags_str = " ".join(tags).lower() if isinstance(tags, list) else ""
    title_match = any(role in title for role in TARGET_ROLES)
    keyword_match = any(kw in description or kw in tags_str for kw in KEYWORDS)
    return title_match or keyword_match
