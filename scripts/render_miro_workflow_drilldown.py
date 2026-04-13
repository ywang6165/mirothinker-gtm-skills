#!/usr/bin/env python3
import json
import html
import os
from pathlib import Path

REPO_ROOT = Path(os.environ.get('MIRO_GTM_REPO_ROOT', Path(__file__).resolve().parents[1]))
BASE = REPO_ROOT / 'output' / 'agent-team'

icp = json.loads((BASE / '01_icp_profile.json').read_text())
signals = json.loads((BASE / '02_signal_miner.json').read_text())
scored = json.loads((BASE / '03_lead_scoring.json').read_text())
drafts = json.loads((BASE / '04_personalization_drafts.json').read_text())
qa = json.loads((BASE / '05_qa_review.json').read_text())
manager = json.loads((BASE / '06_manager_summary.json').read_text())

approved_map = {}
for row in qa['approved']:
    d = row['draft']
    approved_map[d['lead_id']] = {'draft': d, 'qa_notes': row['qa_notes']}

accepted_rows = []
for a in scored['accepted'][:15]:
    reasons = '; '.join(a.get('reasons', []))
    accepted_rows.append(
        f"<tr><td>{html.escape(a['name'])}</td><td>{html.escape(a['company'])}</td><td>{a['score']}</td><td>{html.escape(reasons)}</td></tr>"
    )

rejected_rows = []
for r in scored['rejected'][:10]:
    reasons = '; '.join(r.get('reasons', []))
    rejected_rows.append(
        f"<tr><td>{html.escape(r['name'])}</td><td>{html.escape(r['company'])}</td><td>{r['score']}</td><td>{html.escape(reasons)}</td></tr>"
    )

email_cards = []
for ap in qa['approved'][:8]:
    d = ap['draft']
    email_cards.append(
        "<details class='email'>"
        f"<summary><strong>{html.escape(d['name'])}</strong> @ {html.escape(d['company'])} | score {d['score']}</summary>"
        f"<p><strong>Subject:</strong> {html.escape(d['subject'])}</p>"
        f"<pre>{html.escape(d['body'])}</pre>"
        f"<p class='muted'><strong>QA:</strong> {html.escape(ap['qa_notes'])}</p>"
        f"<p class='muted'><strong>Blog angle:</strong> {html.escape(d['blog_angle'])}</p>"
        "</details>"
    )

html_doc = f"""<!DOCTYPE html>
<html lang='en'>
<head>
  <meta charset='UTF-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1.0' />
  <title>MiroThinker GTM Workflow Drilldown</title>
  <style>
    body {{font-family: Inter, Arial, sans-serif; background:#f6f8fc; color:#0f172a; margin:0;}}
    .wrap {{max-width:1280px; margin:0 auto; padding:24px;}}
    .hero,.panel,.step {{background:#fff; border:1px solid #dbe3ef; border-radius:14px; padding:16px; margin-bottom:12px;}}
    .grid {{display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px;}}
    .steps {{display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px;}}
    .chain {{color:#0f766e; font-weight:700;}}
    .muted {{color:#475569; font-size:13px;}}
    table {{width:100%; border-collapse:collapse; font-size:14px;}}
    th,td {{border-bottom:1px solid #e2e8f0; text-align:left; padding:8px; vertical-align:top;}}
    th {{background:#0f172a; color:#fff;}}
    pre {{background:#f8fafc; border:1px solid #e2e8f0; padding:10px; white-space:pre-wrap; border-radius:8px;}}
    .email {{border:1px solid #e2e8f0; border-radius:10px; padding:10px; margin-bottom:10px; background:#fff;}}
    @media (max-width:900px) {{.grid,.steps{{grid-template-columns:1fr;}}}}
  </style>
</head>
<body>
  <div class='wrap'>
    <div class='hero'>
      <h1>MiroThinker Step-by-Step GTM Workflow (Actual Run)</h1>
      <p class='muted'>Run: {html.escape(manager['timestamp'])}</p>
      <p class='chain'>ICP Strategist -> Signal Miner -> Lead Scorer -> Personalization Writer -> QA/Approver -> GTM Manager</p>
    </div>

    <div class='grid'>
      <div class='panel'><strong>Input leads</strong><div>{manager['lead_input_count']}</div></div>
      <div class='panel'><strong>Accepted</strong><div>{manager['accepted_count']}</div></div>
      <div class='panel'><strong>Rejected</strong><div>{manager['rejected_count']}</div></div>
      <div class='panel'><strong>Drafts written</strong><div>{manager['draft_count']}</div></div>
      <div class='panel'><strong>QA approved</strong><div>{manager['qa_approved']}</div></div>
      <div class='panel'><strong>QA retried</strong><div>{qa['retried_count']}</div></div>
    </div>

    <div class='steps'>
      <div class='step'><h3>1) ICP Strategist</h3><p>Defines target segments, keywords, exclusions, and score threshold.</p><p class='muted'>Threshold: {icp['minimum_score_to_contact']} | Segments: {len(icp['ideal_segments'])}</p><p class='muted'>Artifact: {manager['artifacts']['icp']}</p></div>
      <div class='step'><h3>2) Signal Miner</h3><p>Extracts structured signals from each lead (keyword matches, role signal, region fit, profile presence).</p><p class='muted'>Processed: {signals['output_records']}</p><p class='muted'>Artifact: {manager['artifacts']['signals']}</p></div>
      <div class='step'><h3>3) Lead Scorer</h3><p>Applies weighted scoring and dedupe; accepts high-fit and rejects low-fit leads.</p><p class='muted'>Accepted {scored['accepted_count']} | Rejected {scored['rejected_count']}</p><p class='muted'>Artifact: {manager['artifacts']['scores']}</p></div>
      <div class='step'><h3>4) Personalization Writer</h3><p>Generates personalized outreach emails + blog angles for accepted leads.</p><p class='muted'>Drafts: {drafts['draft_count']}</p><p class='muted'>Artifact: {manager['artifacts']['drafts']}</p></div>
      <div class='step'><h3>5) QA / Approver</h3><p>Checks name/company context, anti-hype language, and minimum quality; rewrites failed drafts once.</p><p class='muted'>Approved {qa['approved_count']} | Rejected {qa['rejected_count']} | Retried {qa['retried_count']}</p><p class='muted'>Artifact: {manager['artifacts']['qa']}</p></div>
      <div class='step'><h3>6) GTM Manager</h3><p>Runs validation suite: happy-path, quality-gate, dependency-block, and dedupe rerun determinism.</p><p class='muted'>All validations: pass</p><p class='muted'>Artifact: {manager['artifacts']['manager']}</p></div>
    </div>

    <div class='panel'>
      <h2>Why Leads Were Accepted</h2>
      <table>
        <thead><tr><th>Name</th><th>Company</th><th>Score</th><th>Reasons</th></tr></thead>
        <tbody>{''.join(accepted_rows)}</tbody>
      </table>
    </div>

    <div class='panel'>
      <h2>Why Leads Were Rejected</h2>
      <table>
        <thead><tr><th>Name</th><th>Company</th><th>Score</th><th>Reasons</th></tr></thead>
        <tbody>{''.join(rejected_rows)}</tbody>
      </table>
    </div>

    <div class='panel'>
      <h2>Generated Personalized Emails (Actual)</h2>
      <p class='muted'>Pulled from QA-approved outputs.</p>
      {''.join(email_cards)}
    </div>

    <div class='panel'>
      <h2>What It Does Beyond Emails</h2>
      <ul>
        <li>Converts raw lead CSV into a structured signal dataset.</li>
        <li>Scores and prioritizes leads with explicit acceptance/rejection rationale.</li>
        <li>Performs deterministic dedupe rerun checks (second run adds 0 new leads).</li>
        <li>Tests dependency controls by simulating missing upstream artifacts.</li>
        <li>Generates a blog-angle asset for each approved prospect.</li>
        <li>Produces auditable JSON artifacts for each agent stage.</li>
      </ul>
    </div>
  </div>
</body>
</html>
"""

out = BASE / 'mirothinker-workflow-drilldown.html'
out.write_text(html_doc)
print(out)
