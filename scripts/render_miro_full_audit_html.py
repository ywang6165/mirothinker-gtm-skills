#!/usr/bin/env python3
import json
import html
import os
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(os.environ.get('MIRO_GTM_REPO_ROOT', Path(__file__).resolve().parents[1]))
BASE = REPO_ROOT / 'output' / 'agent-team'
OUT = BASE / 'mirothinker-gtm-full-walkthrough.html'
BASE_REL = BASE.relative_to(REPO_ROOT).as_posix()
OUT_REL = OUT.relative_to(REPO_ROOT).as_posix()

icp = json.loads((BASE / '01_icp_profile.json').read_text())
signals = json.loads((BASE / '02_signal_miner.json').read_text())
scored = json.loads((BASE / '03_lead_scoring.json').read_text())
drafts = json.loads((BASE / '04_personalization_drafts.json').read_text())
qa = json.loads((BASE / '05_qa_review.json').read_text())
manager = json.loads((BASE / '06_manager_summary.json').read_text())
latest_path = BASE / 'latest_run_stdout.json'
if latest_path.exists():
    last_run = json.loads(latest_path.read_text(encoding='utf-8'))
else:
    # Fallback when only manager artifact exists.
    last_run = {'manager': manager, 'source_csv': manager.get('source_csv', '')}

kw_counter = Counter()
for rec in signals['records']:
    for kw in rec['signals']['matched_keywords']:
        kw_counter[kw] += 1

accepted_rows = []
for rec in scored['accepted']:
    accepted_rows.append(
        "<tr>"
        f"<td>{html.escape(rec['lead_id'])}</td>"
        f"<td>{html.escape(rec['name'])}</td>"
        f"<td>{html.escape(rec['company'])}</td>"
        f"<td>{html.escape(rec['title'])}</td>"
        f"<td>{rec['score']}</td>"
        f"<td>{html.escape(rec['band'])}</td>"
        f"<td>{html.escape('; '.join(rec['reasons']))}</td>"
        "</tr>"
    )

rejected_rows = []
for rec in scored['rejected']:
    rejected_rows.append(
        "<tr>"
        f"<td>{html.escape(rec['lead_id'])}</td>"
        f"<td>{html.escape(rec['name'])}</td>"
        f"<td>{html.escape(rec['company'])}</td>"
        f"<td>{html.escape(rec['title'])}</td>"
        f"<td>{rec['score']}</td>"
        f"<td>{html.escape(rec['band'])}</td>"
        f"<td>{html.escape('; '.join(rec['reasons']))}</td>"
        "</tr>"
    )

email_blocks = []
for item in qa['approved']:
    draft = item['draft']
    email_blocks.append(
        "<details class='email-block'>"
        f"<summary><strong>{html.escape(draft['name'])}</strong> | {html.escape(draft['company'])} | score {draft['score']}</summary>"
        f"<p><strong>Subject:</strong> {html.escape(draft['subject'])}</p>"
        f"<pre>{html.escape(draft['body'])}</pre>"
        f"<p class='muted'><strong>QA note:</strong> {html.escape(item['qa_notes'])}</p>"
        f"<p class='muted'><strong>Blog angle:</strong> {html.escape(draft['blog_angle'])}</p>"
        "</details>"
    )

keyword_rows = [f"<tr><td>{html.escape(k)}</td><td>{v}</td></tr>" for k, v in kw_counter.most_common()]

# Show an exact formula as implemented.
scoring_formula = """
Base score = 0
+30 if title includes one of: head, director, vp, chief, principal, lead
+10 per matched signal keyword (cap +30)
+10 if region includes preferred countries (US/UK/Canada/Singapore)
+5 if LinkedIn profile exists
-15 if company contains "university"
-50 if title/name includes exclusion keywords (student, intern, recruiter, advisor)
Accept if score >= 45
Band: A>=65, B>=45, C<45
""".strip()

html_doc = f"""<!DOCTYPE html>
<html lang='en'>
<head>
  <meta charset='UTF-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1.0' />
  <title>MiroThinker GTM Full Walkthrough</title>
  <style>
    body {{ font-family: Inter, Arial, sans-serif; margin:0; background:#f5f7fb; color:#0f172a; }}
    .wrap {{ max-width: 1360px; margin: 0 auto; padding: 24px; }}
    .panel {{ background:#fff; border:1px solid #dbe3ef; border-radius:14px; padding:16px; margin-bottom:12px; }}
    h1,h2,h3 {{ margin:0 0 10px; }}
    .muted {{ color:#475569; font-size:13px; }}
    .chain {{ color:#0f766e; font-weight:700; }}
    .kpis {{ display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:10px; }}
    .kpi {{ background:#fff; border:1px solid #dbe3ef; border-radius:12px; padding:12px; }}
    table {{ width:100%; border-collapse:collapse; font-size:13px; }}
    th, td {{ border-bottom:1px solid #e2e8f0; text-align:left; padding:8px; vertical-align:top; }}
    th {{ background:#0f172a; color:#fff; position:sticky; top:0; }}
    .table-wrap {{ max-height:420px; overflow:auto; border:1px solid #dbe3ef; border-radius:10px; }}
    code, pre {{ background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; }}
    code {{ padding:2px 5px; }}
    pre {{ padding:10px; white-space:pre-wrap; }}
    .email-block {{ border:1px solid #dbe3ef; border-radius:10px; padding:10px; margin-bottom:10px; background:#fff; }}
    .cols {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
    @media (max-width:1100px) {{ .kpis{{grid-template-columns:repeat(2,minmax(0,1fr));}} .cols{{grid-template-columns:1fr;}} }}
  </style>
</head>
<body>
  <div class='wrap'>
    <div class='panel'>
      <h1>MiroThinker GTM Agents Team - Full Technical Walkthrough</h1>
      <p class='muted'>This is the full evidence package from the latest run. It is meant to prove reproducible real outputs, not a conceptual overview.</p>
      <p class='chain'>Dependency chain: ICP Strategist -> Signal Miner -> Lead Scorer -> Personalization Writer -> QA/Approver -> GTM Manager</p>
      <p class='muted'>Latest run timestamp: {html.escape(last_run['manager']['timestamp'])}</p>
      <p class='muted'>Source lead dataset: <code>{html.escape(last_run['source_csv'])}</code></p>
    </div>

    <div class='kpis'>
      <div class='kpi'><strong>Input leads</strong><div>{manager['lead_input_count']}</div></div>
      <div class='kpi'><strong>Accepted leads</strong><div>{manager['accepted_count']}</div></div>
      <div class='kpi'><strong>Rejected leads</strong><div>{manager['rejected_count']}</div></div>
      <div class='kpi'><strong>Drafts generated</strong><div>{manager['draft_count']}</div></div>
      <div class='kpi'><strong>QA retried</strong><div>{qa['retried_count']}</div></div>
      <div class='kpi'><strong>Dedupe run-2 new</strong><div>{manager['dedupe']['second_run_new']}</div></div>
    </div>

    <div class='panel'>
      <h2>What You Did (Operator Actions)</h2>
      <ol>
        <li>Provided live data credentials and selected MiroThinker scope.</li>
        <li>Ran SQL in Supabase SQL Editor to provision required tables.</li>
        <li>Confirmed project path rename and Goose repository path updates.</li>
        <li>Requested real runs, then requested full dependency-validated agent presentation.</li>
      </ol>
      <p class='muted'>Outcome: pipeline executed on real CrustData CSV and produced full artifacts in <code>{html.escape(BASE_REL)}</code>.</p>
    </div>

    <div class='cols'>
      <div class='panel'>
        <h2>Agent-by-Agent Exact Output Contract</h2>
        <ol>
          <li><strong>ICP Strategist</strong>: emits target segments, title rules, keyword set, exclusions, threshold.</li>
          <li><strong>Signal Miner</strong>: emits normalized lead signals per lead_id.</li>
          <li><strong>Lead Scorer</strong>: emits accepted/rejected arrays with numeric score + reasons.</li>
          <li><strong>Personalization Writer</strong>: emits subject/body/blog angle drafts for top accepted leads.</li>
          <li><strong>QA/Approver</strong>: emits approved/rejected drafts with QA notes and retry evidence.</li>
          <li><strong>GTM Manager</strong>: emits validation status, dependency test, dedupe determinism, artifact index.</li>
        </ol>
      </div>
      <div class='panel'>
        <h2>Decision Engine (Exact Logic)</h2>
        <pre>{html.escape(scoring_formula)}</pre>
        <p class='muted'>ICP threshold from artifact: <strong>{icp['minimum_score_to_contact']}</strong></p>
      </div>
    </div>

    <div class='cols'>
      <div class='panel'>
        <h2>Validation Proofs</h2>
        <ul>
          <li>Happy-path: <strong>{manager['validation']['happy_path']}</strong></li>
          <li>Quality-gate: <strong>{manager['validation']['quality_gate']}</strong></li>
          <li>Dependency-proof: <strong>{manager['validation']['dependency_proof']}</strong></li>
          <li>Dedupe-rerun: <strong>{manager['validation']['dedupe_rerun']}</strong></li>
        </ul>
        <p class='muted'>Dependency simulation: {html.escape(manager['dependency_proof']['message'])}</p>
      </div>
      <div class='panel'>
        <h2>Data Gathered (Signals)</h2>
        <div class='table-wrap'>
          <table>
            <thead><tr><th>Keyword</th><th>Matched leads</th></tr></thead>
            <tbody>{''.join(keyword_rows)}</tbody>
          </table>
        </div>
      </div>
    </div>

    <div class='panel'>
      <h2>Accepted Lead Decisions (All)</h2>
      <div class='table-wrap'>
        <table>
          <thead><tr><th>Lead ID</th><th>Name</th><th>Company</th><th>Title</th><th>Score</th><th>Band</th><th>Decision reasons</th></tr></thead>
          <tbody>{''.join(accepted_rows)}</tbody>
        </table>
      </div>
    </div>

    <div class='panel'>
      <h2>Rejected Lead Decisions (All)</h2>
      <div class='table-wrap'>
        <table>
          <thead><tr><th>Lead ID</th><th>Name</th><th>Company</th><th>Title</th><th>Score</th><th>Band</th><th>Decision reasons</th></tr></thead>
          <tbody>{''.join(rejected_rows)}</tbody>
        </table>
      </div>
    </div>

    <div class='panel'>
      <h2>Generated Personalized Emails (QA Approved)</h2>
      <p class='muted'>These are the exact generated outputs (subject/body/blog-angle) after QA checks.</p>
      {''.join(email_blocks)}
    </div>

    <div class='panel'>
      <h2>What It Does Besides Email</h2>
      <ul>
        <li>Lead signal mining and normalization from raw source records.</li>
        <li>Deterministic scoring, ranking, and explicit rejection logic.</li>
        <li>Artifact dependency gating between upstream/downstream agents.</li>
        <li>Quality control with retry rewrite path (anti-hype and personalization checks).</li>
        <li>Dedupe reproducibility check across reruns.</li>
        <li>Per-lead blog content-angle generation for content-led GTM.</li>
        <li>Machine-auditable JSON outputs for every stage.</li>
      </ul>
    </div>

    <div class='panel'>
      <h2>How to Reproduce Real Results</h2>
      <pre>python3 scripts/miro_gtm_agent_team.py
python3 scripts/render_miro_workflow_drilldown.py
python3 scripts/render_miro_full_audit_html.py</pre>
      <p class='muted'>Main artifacts: <code>{html.escape((BASE / '06_manager_summary.json').relative_to(REPO_ROOT).as_posix())}</code>, <code>{html.escape(OUT_REL)}</code></p>
    </div>
  </div>
</body>
</html>
"""

OUT.write_text(html_doc, encoding='utf-8')
print(OUT)
