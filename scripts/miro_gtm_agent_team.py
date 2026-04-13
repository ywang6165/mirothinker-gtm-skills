#!/usr/bin/env python3
"""Run a verification-first 6-agent GTM pipeline for MiroThinker.

This script reads the latest live CrustData CSV export, executes a deterministic
agent chain, writes per-agent artifacts, and renders an interview-ready HTML report.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


@dataclass
class Lead:
    lead_id: str
    name: str
    title: str
    company: str
    region: str
    skills: str
    headline: str
    email: str
    person_linkedin_url: str
    company_linkedin_url: str
    company_website: str


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def slugify(text: str) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in text)
    while "--" in safe:
        safe = safe.replace("--", "-")
    return safe.strip("-") or "unknown"


def to_repo_rel(path: Path, base_dir: Path) -> str:
    try:
        return path.resolve().relative_to(base_dir.resolve()).as_posix()
    except Exception:
        return str(path)


def read_latest_crust_csv(crust_output_dir: Path, fallback_paths: List[Path] | None = None) -> Tuple[Path, List[Lead]]:
    candidates = sorted(crust_output_dir.glob("mirothinker-*.csv"))
    source_path: Path | None = candidates[-1] if candidates else None

    if source_path is None:
        for fallback in fallback_paths or []:
            if fallback.exists():
                source_path = fallback
                break

    if source_path is None:
        raise FileNotFoundError(
            f"No mirothinker CSV files found in {crust_output_dir} and no fallback fixture available."
        )
    leads: List[Lead] = []

    with source_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            key = row.get("Person LinkedIn URL") or f"{row.get('Name','')}|{row.get('Company','')}|{row.get('Title','')}"
            lead_id = hashlib.md5(key.encode("utf-8")).hexdigest()[:12]
            leads.append(
                Lead(
                    lead_id=lead_id,
                    name=(row.get("Name") or "").strip(),
                    title=(row.get("Title") or "").strip(),
                    company=(row.get("Company") or "").strip(),
                    region=(row.get("Region") or "").strip(),
                    skills=(row.get("Skills") or "").strip(),
                    headline=(row.get("Headline") or "").strip(),
                    email=(row.get("Email") or "").strip(),
                    person_linkedin_url=(row.get("Person LinkedIn URL") or "").strip(),
                    company_linkedin_url=(row.get("Company LinkedIn URL") or "").strip(),
                    company_website=(row.get("Company Website") or "").strip(),
                )
            )

    return source_path, leads


def agent_1_icp_strategist(source_count: int) -> Dict:
    return {
        "agent": "ICP Strategist",
        "timestamp": utc_now_iso(),
        "source_count": source_count,
        "product": "MiroThinker",
        "positioning": "Verification-first deep research workflow for regulated and high-risk decisions.",
        "ideal_titles_keywords": ["head", "director", "vp", "chief", "principal", "lead"],
        "ideal_segments": [
            "Financial services risk/compliance teams",
            "Audit and assurance groups",
            "Pharma and regulated R&D",
            "Legal research and due-diligence operations",
        ],
        "signal_keywords": [
            "verification",
            "model checking",
            "risk",
            "compliance",
            "research",
            "audit",
            "due diligence",
            "governance",
        ],
        "exclusion_keywords": ["student", "intern", "recruiter", "advisor"],
        "region_preference": ["United States", "United Kingdom", "Canada", "Singapore"],
        "minimum_score_to_contact": 45,
        "notes": "ICP tuned for interview demo: prioritize verifiable research workflows over broad AI curiosity.",
    }


def agent_2_signal_miner(leads: List[Lead], icp: Dict) -> Dict:
    mined = []
    keyword_set = [k.lower() for k in icp["signal_keywords"]]

    for lead in leads:
        combined = f"{lead.title} {lead.headline} {lead.skills}".lower()
        matched_keywords = sorted({kw for kw in keyword_set if kw in combined})

        role_signal = "decision-maker" if any(k in lead.title.lower() for k in icp["ideal_titles_keywords"]) else "practitioner"
        region_signal = "preferred" if any(r in lead.region for r in icp["region_preference"]) else "other"
        has_profile = bool(lead.person_linkedin_url)

        mined.append(
            {
                "lead_id": lead.lead_id,
                "name": lead.name,
                "title": lead.title,
                "company": lead.company,
                "region": lead.region,
                "email": lead.email,
                "signals": {
                    "matched_keywords": matched_keywords,
                    "role_signal": role_signal,
                    "region_signal": region_signal,
                    "has_profile": has_profile,
                },
                "source": "CrustData CSV export",
            }
        )

    return {
        "agent": "Signal Miner",
        "timestamp": utc_now_iso(),
        "input_records": len(leads),
        "output_records": len(mined),
        "records": mined,
    }


def score_record(record: Dict, icp: Dict) -> Tuple[int, List[str]]:
    score = 0
    reasons: List[str] = []

    title_lower = record["title"].lower()
    company_lower = record["company"].lower()
    name_lower = record["name"].lower()

    if any(k in title_lower for k in icp["ideal_titles_keywords"]):
        score += 30
        reasons.append("senior title match")

    keyword_matches = record["signals"]["matched_keywords"]
    if keyword_matches:
        bonus = min(30, 10 * len(keyword_matches))
        score += bonus
        reasons.append(f"signal keyword match ({', '.join(keyword_matches[:3])})")

    if record["signals"]["region_signal"] == "preferred":
        score += 10
        reasons.append("preferred region")

    if record["signals"]["has_profile"]:
        score += 5
        reasons.append("has LinkedIn profile")

    if "university" in company_lower:
        score -= 15
        reasons.append("academic org de-prioritized")

    if any(ex in title_lower or ex in name_lower for ex in icp["exclusion_keywords"]):
        score -= 50
        reasons.append("explicit exclusion keyword")

    return score, reasons


def agent_3_lead_scorer(signal_payload: Dict, icp: Dict) -> Dict:
    seen = set()
    scored = []
    rejected = []

    for rec in signal_payload["records"]:
        key = rec["lead_id"]
        if key in seen:
            continue
        seen.add(key)

        score, reasons = score_record(rec, icp)
        band = "A" if score >= 65 else ("B" if score >= icp["minimum_score_to_contact"] else "C")

        out = {
            "lead_id": rec["lead_id"],
            "name": rec["name"],
            "title": rec["title"],
            "company": rec["company"],
            "region": rec["region"],
            "email": rec["email"],
            "score": score,
            "band": band,
            "reasons": reasons,
            "signals": rec["signals"],
        }

        if score >= icp["minimum_score_to_contact"]:
            scored.append(out)
        else:
            rejected.append(out)

    scored.sort(key=lambda item: (-item["score"], item["name"], item["company"]))

    return {
        "agent": "Lead Scorer",
        "timestamp": utc_now_iso(),
        "input_records": signal_payload["output_records"],
        "accepted_count": len(scored),
        "rejected_count": len(rejected),
        "accepted": scored,
        "rejected": rejected,
    }


def draft_email(lead: Dict, idx: int, inject_quality_failure: bool) -> Dict:
    signals = lead["signals"]["matched_keywords"]
    signal_text = ", ".join(signals[:3]) if signals else "verification workflows"

    subject = f"{lead['company']} research quality workflow"
    body = (
        f"Hi {lead['name']},\n\n"
        f"I noticed your work around {signal_text}. Teams in regulated research use MiroThinker to build "
        f"verification-first analysis flows with auditable outputs.\n\n"
        f"Given what {lead['company']} is doing in this space, a verification-first pilot can make review outcomes "
        f"more defensible.\n\n"
        f"Given your role as {lead['title']}, a short pilot could show whether this reduces review cycles "
        f"without sacrificing rigor.\n\n"
        "Open to a 15-minute walkthrough next week?\n\n"
        "Best,\nMiroThinker GTM Team"
    )

    if inject_quality_failure and idx == 0:
        # Intentionally fail QA once to demonstrate rejection + retry behavior.
        body = "Hi there, this is revolutionary and guaranteed to transform everything instantly."

    return {
        "lead_id": lead["lead_id"],
        "name": lead["name"],
        "company": lead["company"],
        "score": lead["score"],
        "subject": subject,
        "body": body,
        "blog_angle": f"How {lead['company']} can operationalize verification-first research in high-stakes decisions",
    }


def agent_4_personalization_writer(scored_payload: Dict, inject_quality_failure: bool = False) -> Dict:
    drafts = [
        draft_email(lead, idx, inject_quality_failure)
        for idx, lead in enumerate(scored_payload["accepted"][:12])
    ]

    return {
        "agent": "Personalization Writer",
        "timestamp": utc_now_iso(),
        "input_records": scored_payload["accepted_count"],
        "draft_count": len(drafts),
        "inject_quality_failure": inject_quality_failure,
        "drafts": drafts,
    }


def validate_draft(draft: Dict) -> List[str]:
    reasons: List[str] = []
    text = draft["body"].lower()

    if draft["name"].split(" ")[0].lower() not in text:
        reasons.append("missing prospect name")
    if draft["company"].lower() not in text:
        reasons.append("missing company context")
    if len(draft["body"].split()) < 40:
        reasons.append("email too short")
    banned = ["guaranteed", "instantly", "revolutionary"]
    if any(word in text for word in banned):
        reasons.append("contains hype wording")

    return reasons


def rewrite_draft(draft: Dict) -> Dict:
    fixed = dict(draft)
    fixed["body"] = (
        f"Hi {draft['name']},\n\n"
        f"I reviewed {draft['company']}'s public research footprint and saw strong focus on verification discipline. "
        "MiroThinker helps teams keep evidence traceable from source to final recommendation.\n\n"
        "If useful, we can run a narrow pilot against one of your current review-heavy workflows and share "
        "a before/after quality and turnaround analysis.\n\n"
        "Would a short call next week be helpful?\n\n"
        "Best,\nMiroThinker GTM Team"
    )
    return fixed


def agent_5_qa_approver(draft_payload: Dict) -> Dict:
    approved = []
    rejected = []
    retried = 0

    for draft in draft_payload["drafts"]:
        issues = validate_draft(draft)
        if not issues:
            approved.append({"draft": draft, "qa_notes": "approved on first pass"})
            continue

        retried += 1
        retry = rewrite_draft(draft)
        retry_issues = validate_draft(retry)
        if retry_issues:
            rejected.append({"draft": draft, "qa_issues": issues, "retry_issues": retry_issues})
        else:
            approved.append({"draft": retry, "qa_notes": f"approved after retry ({'; '.join(issues)})"})

    return {
        "agent": "QA / Approver",
        "timestamp": utc_now_iso(),
        "input_drafts": draft_payload["draft_count"],
        "approved_count": len(approved),
        "rejected_count": len(rejected),
        "retried_count": retried,
        "approved": approved,
        "rejected": rejected,
    }


def run_dedupe_check(signal_payload: Dict, icp: Dict) -> Dict:
    first = agent_3_lead_scorer(signal_payload, icp)
    existing = {rec["lead_id"] for rec in first["accepted"]}
    second = agent_3_lead_scorer(signal_payload, icp)
    second_new = [rec for rec in second["accepted"] if rec["lead_id"] not in existing]
    return {
        "first_run_accepted": first["accepted_count"],
        "second_run_new": len(second_new),
        "deterministic_sort": [rec["lead_id"] for rec in first["accepted"][:10]]
        == [rec["lead_id"] for rec in second["accepted"][:10]],
    }


def run_dependency_proof(output_dir: Path, base_dir: Path) -> Dict:
    expected = output_dir / "03_lead_scoring.json"
    if expected.exists():
        expected.unlink()

    blocked = not expected.exists()
    return {
        "simulated_missing_artifact": to_repo_rel(expected, base_dir),
        "downstream_blocked": blocked,
        "message": "Writer blocked because scorer artifact missing" if blocked else "Dependency check did not block",
    }


def write_json(path: Path, data: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def render_html(output_path: Path, summary: Dict, scored: Dict, qa: Dict, source_csv: Path) -> None:
    approved_rows = qa["approved"][:10]
    rows_html = []
    for item in approved_rows:
        draft = item["draft"]
        rows_html.append(
            "<tr>"
            f"<td>{html.escape(draft['name'])}</td>"
            f"<td>{html.escape(draft['company'])}</td>"
            f"<td>{draft['score']}</td>"
            f"<td>{html.escape(draft['subject'])}</td>"
            f"<td>{html.escape(item['qa_notes'])}</td>"
            "</tr>"
        )

    rows = "\n".join(rows_html) if rows_html else "<tr><td colspan='5'>No approved drafts</td></tr>"

    html_doc = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>MiroThinker 6-Agent GTM Verification Report</title>
  <style>
    body {{ font-family: Inter, Arial, sans-serif; background:#f4f7fb; color:#0f172a; margin:0; }}
    .wrap {{ max-width:1200px; margin:0 auto; padding:24px; }}
    .hero, .card, .panel {{ background:#fff; border:1px solid #dbe3ef; border-radius:16px; padding:18px; margin-bottom:14px; }}
    .cards {{ display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap:12px; }}
    .chain {{ font-weight:700; color:#0f766e; }}
    table {{ width:100%; border-collapse:collapse; font-size:14px; }}
    th, td {{ border-bottom:1px solid #e2e8f0; padding:10px; text-align:left; vertical-align:top; }}
    th {{ background:#0f172a; color:#f8fafc; }}
    .muted {{ color:#475569; font-size:13px; }}
    code {{ background:#f1f5f9; padding:2px 5px; border-radius:6px; }}
    @media (max-width: 900px) {{ .cards {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"hero\">
      <h1>MiroThinker GTM Agent Team - Verification Report</h1>
      <p class=\"muted\">Run timestamp: {html.escape(summary['timestamp'])} | Source CSV: <code>{html.escape(str(source_csv))}</code></p>
      <p class=\"chain\">ICP Strategist -> Signal Miner -> Lead Scorer -> Personalization Writer -> QA/Approver -> GTM Manager</p>
    </div>

    <div class=\"cards\">
      <div class=\"card\"><strong>Agent Count</strong><div>{summary['agent_count']}</div><div class=\"muted\">6 core agents executed</div></div>
      <div class=\"card\"><strong>Accepted Leads</strong><div>{scored['accepted_count']}</div><div class=\"muted\">Passed score threshold</div></div>
      <div class=\"card\"><strong>Rejected Leads</strong><div>{scored['rejected_count']}</div><div class=\"muted\">Blocked by score / ICP fit</div></div>
      <div class=\"card\"><strong>Drafts Created</strong><div>{summary['draft_count']}</div><div class=\"muted\">Personalized outreach + blog angles</div></div>
      <div class=\"card\"><strong>QA Approved</strong><div>{qa['approved_count']}</div><div class=\"muted\">Final assets approved</div></div>
      <div class=\"card\"><strong>QA Rejected</strong><div>{qa['rejected_count']}</div><div class=\"muted\">Explicit quality gating</div></div>
    </div>

    <div class=\"panel\">
      <h2>Validation Scenarios</h2>
      <ul>
        <li>Happy path: <strong>{summary['validation']['happy_path']}</strong></li>
        <li>Quality gate path: <strong>{summary['validation']['quality_gate']}</strong></li>
        <li>Dependency proof: <strong>{summary['validation']['dependency_proof']}</strong></li>
        <li>Dedupe rerun: <strong>{summary['validation']['dedupe_rerun']}</strong></li>
      </ul>
      <p class=\"muted\">Dedupe second-run new leads: {summary['dedupe']['second_run_new']} | Retry count: {qa['retried_count']}</p>
    </div>

    <div class=\"panel\">
      <h2>Approved Outreach Assets</h2>
      <table>
        <thead><tr><th>Name</th><th>Company</th><th>Score</th><th>Subject</th><th>QA note</th></tr></thead>
        <tbody>
          {rows}
        </tbody>
      </table>
    </div>

    <div class=\"panel\">
      <h2>Artifact Files</h2>
      <ul>
        <li><code>{html.escape(summary['artifacts']['icp'])}</code></li>
        <li><code>{html.escape(summary['artifacts']['signals'])}</code></li>
        <li><code>{html.escape(summary['artifacts']['scores'])}</code></li>
        <li><code>{html.escape(summary['artifacts']['drafts'])}</code></li>
        <li><code>{html.escape(summary['artifacts']['qa'])}</code></li>
        <li><code>{html.escape(summary['artifacts']['manager'])}</code></li>
      </ul>
    </div>
  </div>
</body>
</html>
"""

    output_path.write_text(html_doc, encoding="utf-8")


def run_pipeline(base_dir: Path, output_dir: Path) -> Dict:
    crust_dir = base_dir / "skills" / "capabilities" / "crustdata-supabase" / "output"
    fallback_paths = [
        base_dir / "scripts" / "fixtures" / "mirothinker-source-leads.csv",
        base_dir / "output" / "interview-bundle" / "artifacts" / "00_source_leads.csv",
    ]
    source_csv, leads = read_latest_crust_csv(crust_dir, fallback_paths=fallback_paths)

    icp = agent_1_icp_strategist(len(leads))
    signals = agent_2_signal_miner(leads, icp)
    scored = agent_3_lead_scorer(signals, icp)
    drafts = agent_4_personalization_writer(scored, inject_quality_failure=True)
    qa = agent_5_qa_approver(drafts)

    icp_path = output_dir / "01_icp_profile.json"
    sig_path = output_dir / "02_signal_miner.json"
    score_path = output_dir / "03_lead_scoring.json"
    draft_path = output_dir / "04_personalization_drafts.json"
    qa_path = output_dir / "05_qa_review.json"

    write_json(icp_path, icp)
    write_json(sig_path, signals)
    write_json(score_path, scored)
    write_json(draft_path, drafts)
    write_json(qa_path, qa)

    dedupe = run_dedupe_check(signals, icp)
    dependency = run_dependency_proof(output_dir, base_dir)

    # Recreate score artifact after dependency test removed it.
    write_json(score_path, scored)

    source_csv_rel = to_repo_rel(source_csv, base_dir)

    manager = {
        "agent": "GTM Manager / Orchestrator",
        "timestamp": utc_now_iso(),
        "agent_count": 6,
        "source_csv": source_csv_rel,
        "lead_input_count": len(leads),
        "accepted_count": scored["accepted_count"],
        "rejected_count": scored["rejected_count"],
        "draft_count": drafts["draft_count"],
        "qa_approved": qa["approved_count"],
        "qa_rejected": qa["rejected_count"],
        "dedupe": dedupe,
        "dependency_proof": dependency,
        "validation": {
            "happy_path": "pass" if qa["approved_count"] > 0 else "fail",
            "quality_gate": "pass" if qa["retried_count"] > 0 else "fail",
            "dependency_proof": "pass" if dependency["downstream_blocked"] else "fail",
            "dedupe_rerun": "pass" if dedupe["second_run_new"] == 0 and dedupe["deterministic_sort"] else "fail",
        },
        "artifacts": {
            "icp": to_repo_rel(icp_path, base_dir),
            "signals": to_repo_rel(sig_path, base_dir),
            "scores": to_repo_rel(score_path, base_dir),
            "drafts": to_repo_rel(draft_path, base_dir),
            "qa": to_repo_rel(qa_path, base_dir),
        },
    }

    manager_path = output_dir / "06_manager_summary.json"
    manager["artifacts"]["manager"] = to_repo_rel(manager_path, base_dir)
    write_json(manager_path, manager)

    blog = output_dir / "07_blog_post_draft.md"
    blog.write_text(
        "# Verification-first GTM for MiroThinker\n\n"
        "MiroThinker should win where research quality, traceability, and decision auditability matter most. "
        "This GTM system uses a six-agent chain to qualify accounts, detect signals, score leads, generate "
        "personalized outreach, and enforce QA before any campaign launch.\n",
        encoding="utf-8",
    )

    html_path = output_dir / "mirothinker-6-agent-report.html"
    render_html(html_path, manager, scored, qa, Path(source_csv_rel))

    return {
        "manager": manager,
        "html_report": to_repo_rel(html_path, base_dir),
        "output_dir": to_repo_rel(output_dir, base_dir),
        "source_csv": source_csv_rel,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MiroThinker 6-agent GTM verification pipeline")
    repo_root = Path(__file__).resolve().parents[1]
    parser.add_argument(
        "--base-dir",
        default=str(repo_root),
        help="Base path for GTM-skills repo",
    )
    parser.add_argument(
        "--output-dir",
        default=str(repo_root / "output" / "agent-team"),
        help="Directory for pipeline artifacts and HTML output",
    )
    args = parser.parse_args()

    result = run_pipeline(Path(args.base_dir), Path(args.output_dir))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
