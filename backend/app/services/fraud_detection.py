import re
from datetime import datetime
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def parse_year(date_str: str) -> int | None:
    if not date_str:
        return None
    # Extract 4-digit year
    match = re.search(r"\b(19|20)\d{2}\b", str(date_str))
    if match:
        return int(match.group(0))
    return None


def parse_month_year(date_str: str) -> tuple[int, int] | None:
    """Parse month and year from a date string. Returns (year, month) or None."""
    if not date_str:
        return None
    date_str = str(date_str).lower().strip()
    
    if "present" in date_str or "current" in date_str or "now" in date_str:
        now = datetime.utcnow()
        return (now.year, now.month)
    
    month_map = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    }
    
    year = parse_year(date_str)
    if not year:
        return None
    
    for month_name, month_num in month_map.items():
        if month_name in date_str:
            return (year, month_num)
    
    # Try numeric month
    match = re.search(r"(\d{1,2})[/\-](\d{4})", date_str)
    if match:
        return (int(match.group(2)), int(match.group(1)))
    
    return (year, 6)  # Default to June if only year found


def analyze_fraud(
    employment_records: List[Dict],
    education_records: List[Dict],
    resume_text: str = "",
) -> List[Dict[str, Any]]:
    flags = []

    # ── Check overlapping employment dates ────────────────────────────────────
    parsed_jobs = []
    for job in employment_records:
        start = parse_month_year(job.get("start_date", ""))
        end_str = job.get("end_date", "")
        is_current = job.get("is_current", False)
        
        if is_current or (end_str and ("present" in str(end_str).lower() or "current" in str(end_str).lower())):
            end = (datetime.utcnow().year, datetime.utcnow().month)
        else:
            end = parse_month_year(end_str)
        
        if start:
            parsed_jobs.append({
                "company": job.get("company_name", "Unknown"),
                "title": job.get("job_title", ""),
                "start": start,
                "end": end,
            })

    for i in range(len(parsed_jobs)):
        for j in range(i + 1, len(parsed_jobs)):
            a, b = parsed_jobs[i], parsed_jobs[j]
            if a["start"] and a["end"] and b["start"] and b["end"]:
                a_start = a["start"][0] * 12 + a["start"][1]
                a_end = a["end"][0] * 12 + a["end"][1]
                b_start = b["start"][0] * 12 + b["start"][1]
                b_end = b["end"][0] * 12 + b["end"][1]
                
                overlap = min(a_end, b_end) - max(a_start, b_start)
                if overlap > 2:  # More than 2 months overlap
                    flags.append({
                        "flag_type": "OVERLAPPING_EMPLOYMENT",
                        "description": f"Employment overlap detected between {a['company']} and {b['company']} ({overlap} months)",
                        "severity": "high" if overlap > 6 else "medium",
                        "details": {
                            "company_a": a["company"],
                            "company_b": b["company"],
                            "overlap_months": overlap,
                        },
                    })

    # ── Check impossible timelines ─────────────────────────────────────────────
    for job in employment_records:
        start = parse_month_year(job.get("start_date", ""))
        end = parse_month_year(job.get("end_date", ""))
        if start and end:
            start_val = start[0] * 12 + start[1]
            end_val = end[0] * 12 + end[1]
            if end_val < start_val:
                flags.append({
                    "flag_type": "IMPOSSIBLE_DATES",
                    "description": f"End date before start date at {job.get('company_name', 'Unknown')}",
                    "severity": "high",
                    "details": {"company": job.get("company_name"), "start": job.get("start_date"), "end": job.get("end_date")},
                })
            # Future start date
            now_val = datetime.utcnow().year * 12 + datetime.utcnow().month
            if start_val > now_val + 1:
                flags.append({
                    "flag_type": "FUTURE_EMPLOYMENT",
                    "description": f"Employment start date in the future at {job.get('company_name', 'Unknown')}",
                    "severity": "medium",
                    "details": {"company": job.get("company_name"), "start_date": job.get("start_date")},
                })

    # ── Check education-employment overlap (impossible) ────────────────────────
    for edu in education_records:
        edu_start = parse_year(edu.get("start_year", ""))
        edu_end = parse_year(edu.get("end_year", ""))
        if edu_start and edu_end and (edu_end - edu_start) > 12:
            flags.append({
                "flag_type": "SUSPICIOUS_EDUCATION_DURATION",
                "description": f"Unusually long education duration at {edu.get('institution_name', 'Unknown')}: {edu_end - edu_start} years",
                "severity": "medium",
                "details": {"institution": edu.get("institution_name"), "years": edu_end - edu_start},
            })

    # ── Check for suspicious gaps ─────────────────────────────────────────────
    if len(parsed_jobs) >= 2:
        sorted_jobs = sorted(
            [j for j in parsed_jobs if j["end"]],
            key=lambda x: x["end"][0] * 12 + x["end"][1],
        )
        for i in range(len(sorted_jobs) - 1):
            current_end = sorted_jobs[i]["end"][0] * 12 + sorted_jobs[i]["end"][1]
            next_start_data = parse_month_year(employment_records[i + 1].get("start_date", "")) if i + 1 < len(employment_records) else None
            if next_start_data:
                next_start = next_start_data[0] * 12 + next_start_data[1]
                gap = next_start - current_end
                if gap > 18:
                    flags.append({
                        "flag_type": "SIGNIFICANT_EMPLOYMENT_GAP",
                        "description": f"Employment gap of {gap} months detected",
                        "severity": "low",
                        "details": {"gap_months": gap, "after_company": sorted_jobs[i]["company"]},
                    })

    # ── Keyword stuffing detection ─────────────────────────────────────────────
    if resume_text:
        tech_keywords = ["python", "java", "javascript", "react", "aws", "machine learning",
                         "deep learning", "kubernetes", "docker", "microservices"]
        text_lower = resume_text.lower()
        keyword_count = sum(text_lower.count(kw) for kw in tech_keywords)
        word_count = len(resume_text.split())
        if word_count > 0 and keyword_count / word_count > 0.05:
            flags.append({
                "flag_type": "KEYWORD_STUFFING",
                "description": f"Unusually high density of technical keywords detected ({keyword_count} occurrences in {word_count} words)",
                "severity": "low",
                "details": {"keyword_count": keyword_count, "word_count": word_count},
            })

    # ── Check for very short stints (job hopping) ─────────────────────────────
    short_stints = []
    for job in employment_records:
        start = parse_month_year(job.get("start_date", ""))
        end = parse_month_year(job.get("end_date", ""))
        if start and end and not job.get("is_current"):
            duration = (end[0] * 12 + end[1]) - (start[0] * 12 + start[1])
            if 0 < duration < 3:
                short_stints.append(job.get("company_name", "Unknown"))

    if len(short_stints) >= 3:
        flags.append({
            "flag_type": "EXCESSIVE_JOB_HOPPING",
            "description": f"{len(short_stints)} positions lasted less than 3 months",
            "severity": "low",
            "details": {"companies": short_stints},
        })

    return flags
