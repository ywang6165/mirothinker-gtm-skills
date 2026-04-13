#!/usr/bin/env python3
import json
import os
from pathlib import Path

REPO_ROOT = Path(os.environ.get('MIRO_GTM_REPO_ROOT', Path(__file__).resolve().parents[1]))
CORE = REPO_ROOT / 'output' / 'agent-team'
EXT = REPO_ROOT / 'output' / 'agent-team-extended'
BUNDLE = REPO_ROOT / 'output' / 'interview-bundle'
OUT = BUNDLE / 'index.html'

# Inputs
core_mgr = json.loads((CORE / '06_manager_summary.json').read_text(encoding='utf-8'))
core_sig = json.loads((CORE / '02_signal_miner.json').read_text(encoding='utf-8'))
core_score = json.loads((CORE / '03_lead_scoring.json').read_text(encoding='utf-8'))
core_drafts = json.loads((CORE / '04_personalization_drafts.json').read_text(encoding='utf-8'))
core_qa = json.loads((CORE / '05_qa_review.json').read_text(encoding='utf-8'))

ext_sum = json.loads((EXT / 'run_summary.json').read_text(encoding='utf-8'))
a7 = json.loads((EXT / '07_oss_community_pipeline.json').read_text(encoding='utf-8'))
a8 = json.loads((EXT / '08_benchmark_watchdog.json').read_text(encoding='utf-8'))
a9 = json.loads((EXT / '09_reddit_intent_radar.json').read_text(encoding='utf-8'))
a10 = json.loads((EXT / '10_hn_trend_radar.json').read_text(encoding='utf-8'))
a11 = json.loads((EXT / '11_icp_enrichment_resolver.json').read_text(encoding='utf-8'))
a12 = json.loads((EXT / '12_competitive_intel_synthesizer.json').read_text(encoding='utf-8'))
deps = json.loads((EXT / 'dependencies.json').read_text(encoding='utf-8'))


def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

agent_rows = [
    {
        'id': 'A1', 'name': 'ICP Strategist',
        'personality': 'Strategic, principle-first, risk-aware planner.',
        'what': 'Defines who counts as a good customer fit and sets scoring policy.',
        'count': 'Leads generated: 0 (policy stage)',
        'steps': 'Defines segments -> sets keyword rules -> sets exclusions -> sets threshold.',
        'depends': 'None', 'feeds': 'A2'
    },
    {
        'id': 'A2', 'name': 'Signal Miner',
        'personality': 'Analytical pattern finder; structured and literal.',
        'what': 'Converts raw records into structured signal features.',
        'count': f"Records processed: {core_sig.get('output_records', 0)}",
        'steps': 'Reads profile text -> extracts keywords -> tags role/region/profile.',
        'depends': 'A1, A7, A9', 'feeds': 'A3'
    },
    {
        'id': 'A3', 'name': 'Lead Scorer',
        'personality': 'Strict judge; deterministic and explainable.',
        'what': 'Scores each lead and explicitly accepts/rejects with reasons.',
        'count': f"Accepted: {core_score.get('accepted_count', 0)} | Rejected: {core_score.get('rejected_count', 0)}",
        'steps': 'Applies weighted formula -> assigns band -> stores acceptance reasons.',
        'depends': 'A2', 'feeds': 'A4, A11'
    },
    {
        'id': 'A4', 'name': 'Personalization Writer',
        'personality': 'Empathetic communicator; precise, low-hype tone.',
        'what': 'Writes personalized outreach drafts and blog angles.',
        'count': f"Drafts generated: {core_drafts.get('draft_count', 0)}",
        'steps': 'Reads accepted leads -> drafts subject/body -> adds blog angle per lead.',
        'depends': 'A3, A11, A12', 'feeds': 'A5'
    },
    {
        'id': 'A5', 'name': 'QA Approver',
        'personality': 'Skeptical editor/auditor; anti-hype and quality-first.',
        'what': 'Checks draft quality, retries failures once, approves or blocks.',
        'count': f"Approved: {core_qa.get('approved_count', 0)} | Rejected: {core_qa.get('rejected_count', 0)} | Retries: {core_qa.get('retried_count', 0)}",
        'steps': 'Checks name/company context -> bans hype -> retry rewrite -> final verdict.',
        'depends': 'A4', 'feeds': 'A6'
    },
    {
        'id': 'A6', 'name': 'GTM Orchestrator',
        'personality': 'Ops manager; consistency and reliability obsessed.',
        'what': 'Runs end-to-end execution order and validation checks.',
        'count': "Leads generated: 0 (control and validation stage)",
        'steps': 'Runs sequence -> tests dependency fail-safe -> tests dedupe reproducibility.',
        'depends': 'A1-A5', 'feeds': 'A12 + reporting'
    },
    {
        'id': 'A7', 'name': 'OSS Community Pipeline',
        'personality': 'Community scout; curious and opportunistic.',
        'what': 'Finds and ranks GitHub community prospects.',
        'count': f"Community prospects ranked: {len(a7.get('top_prospects', []))}",
        'steps': 'Fetches stargazers -> enriches profiles -> scores tiers -> emits ranked list.',
        'depends': 'GitHub API', 'feeds': 'A2, A11'
    },
    {
        'id': 'A8', 'name': 'Benchmark Signal Watchdog',
        'personality': 'Competitive sentinel; alert and evidence-driven.',
        'what': 'Monitors benchmark/news chatter and flags threats.',
        'count': f"Threat events flagged: {a8.get('threat_count', 0)}",
        'steps': 'Queries HN -> reads arXiv updates -> ranks threat signals.',
        'depends': 'HN + arXiv', 'feeds': 'A12'
    },
    {
        'id': 'A9', 'name': 'Reddit Intent Radar',
        'personality': 'Demand sensor; pain-point focused.',
        'what': 'Finds high-intent Reddit demand conversations.',
        'count': f"High-intent threads: {len(a9.get('high_intent_posts', []))}",
        'steps': 'Searches intent queries -> scores language signals -> outputs high-intent set.',
        'depends': 'Reddit API', 'feeds': 'A2'
    },
    {
        'id': 'A10', 'name': 'HackerNews Trend Radar',
        'personality': 'Trend watcher; high signal/noise filter.',
        'what': 'Tracks strategic HN threads and deduplicates trend signals.',
        'count': f"Trend threads captured: {a10.get('total_threads', 0)}",
        'steps': 'Runs keyword scans -> dedupes -> ranks by engagement.',
        'depends': 'HN Algolia', 'feeds': 'A8, A12'
    },
    {
        'id': 'A11', 'name': 'ICP Enrichment Resolver',
        'personality': 'Data steward; detail-accurate enricher.',
        'what': 'Enriches accepted leads with persona/domain/link context.',
        'count': f"Leads enriched: {a11.get('enriched_count', 0)}",
        'steps': 'Merges accepted leads with source metadata -> assigns buyer persona.',
        'depends': 'A3, A7', 'feeds': 'A4'
    },
    {
        'id': 'A12', 'name': 'Competitive Intel Synthesizer',
        'personality': 'Narrative strategist; counter-positioning thinker.',
        'what': 'Builds competitor intel and GTM counter-narratives.',
        'count': f"Competitors monitored: {len(a12.get('competitors_monitored', []))}",
        'steps': 'Combines benchmark+trend signals -> scores threat level -> outputs counters.',
        'depends': 'A6, A8, A10', 'feeds': 'A4 + strategy outputs'
    },
]

card_html = ''.join(
    f"""
    <article class='agent'>
      <div class='aid'>{esc(a['id'])}</div>
      <h3>{esc(a['name'])}</h3>
      <p><strong>Personality:</strong> {esc(a['personality'])}</p>
      <p><strong>Main functionality:</strong> {esc(a['what'])}</p>
      <p><strong>Output volume:</strong> {esc(a['count'])}</p>
      <p><strong>Workflow steps:</strong> {esc(a['steps'])}</p>
      <p><strong>Depends on:</strong> {esc(a['depends'])}</p>
      <p><strong>Feeds:</strong> {esc(a['feeds'])}</p>
    </article>
    """ for a in agent_rows
)

exec_steps = [
    ('1', 'Run core orchestration (A1-A6)', 'Built ICP, mined signals, scored leads, wrote drafts, QA checked, manager validated.'),
    ('2', 'Run A7 OSS community scan', 'Fetched GitHub stargazers and produced ranked community prospects.'),
    ('3', 'Run A8 benchmark watchdog', 'Pulled benchmark chatter and papers, flagged threat events.'),
    ('4', 'Run A9 Reddit intent radar', 'Pulled high-intent Reddit posts and scored buying intent language.'),
    ('5', 'Run A10 HN trend radar', 'Collected HN trend threads and deduped by story identity.'),
    ('6', 'Run A11 enrichment resolver', 'Joined accepted leads with source metadata and persona labeling.'),
    ('7', 'Run A12 intel synthesizer', 'Generated competitor threat levels and counter-positioning suggestions.'),
    ('8', 'Build visuals + bundle + deploy', 'Rendered pages, rebuilt share bundle, deployed to Vercel.'),
]

step_rows = ''.join(
    f"<tr><td>{esc(n)}</td><td>{esc(name)}</td><td>{esc(desc)}</td></tr>"
    for n, name, desc in exec_steps
)

zip_instructions = f"""cd {REPO_ROOT / 'output'}
zip -r mirothinker-interview-bundle.zip interview-bundle"""

html = f"""<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='UTF-8' />
<meta name='viewport' content='width=device-width, initial-scale=1.0' />
<title>MiroThinker GTM - Human Friendly Front Page</title>
<style>
body{{margin:0;font-family:Inter,Arial,sans-serif;background:#f5f7fb;color:#0f172a}}
.wrap{{max-width:1350px;margin:0 auto;padding:24px}}
.panel{{background:#fff;border:1px solid #dbe3ef;border-radius:14px;padding:16px;margin-bottom:12px}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}}
.agent{{background:#fff;border:1px solid #dbe3ef;border-radius:12px;padding:12px}}
.aid{{display:inline-block;font-size:12px;font-weight:700;background:#e2e8f0;padding:4px 8px;border-radius:999px;margin-bottom:8px}}
table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{border-bottom:1px solid #e2e8f0;padding:8px;text-align:left;vertical-align:top}}th{{background:#0f172a;color:#fff}}
pre{{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px;white-space:pre-wrap}}
.muted{{color:#475569;font-size:13px}}
.links a{{display:inline-block;margin-right:10px}}
@media(max-width:1000px){{.grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<div class='wrap'>
  <div class='panel'>
    <h1>MiroThinker GTM Agents — What Runs, What It Does, and How It Works Together</h1>
    <p class='muted'>Accuracy checked from run artifacts. This page is intentionally human-friendly and does not show a single "total leads" KPI at top-level.</p>
    <p><strong>Latest extended run:</strong> {esc(ext_sum.get('timestamp'))}</p>
    <div class='links'>
      <a href='artifacts/mirothinker-step-by-step-execution.html' target='_blank'>Execution Trace</a>
      <a href='artifacts/mirothinker-12-agent-graph.html' target='_blank'>Dependency Graph</a>
      <a href='artifacts/extended_run_summary.json' target='_blank'>Run Summary JSON</a>
    </div>
  </div>

  <div class='panel'>
    <h2>How They Work Together on the Front Page</h2>
    <p>The system has two layers: <strong>core execution agents</strong> (A1-A6) that qualify and create outreach assets, and <strong>expansion agents</strong> (A7-A12) that add community demand signals, benchmark intelligence, and enrichment context. Outputs converge into A4 (writer), then A5 (QA), then A6 (orchestrator validation/reporting).</p>
  </div>

  <div class='panel'>
    <h2>Step-by-Step: What We Actually Invoked</h2>
    <table>
      <thead><tr><th>Step</th><th>Action</th><th>What happened</th></tr></thead>
      <tbody>{step_rows}</tbody>
    </table>
  </div>

  <div class='panel'>
    <h2>All Agents, Their Personality, Function, Dependencies, and Output</h2>
    <div class='grid'>
      {card_html}
    </div>
  </div>

  <div class='panel'>
    <h2>Zip Instructions (as requested)</h2>
    <pre>{esc(zip_instructions)}</pre>
  </div>
</div>
</body>
</html>
"""

BUNDLE.mkdir(parents=True, exist_ok=True)
OUT.write_text(html, encoding='utf-8')
print(OUT)
