#!/usr/bin/env python3
"""Run a reproducible, no-secrets validation flow for interviewers."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_DIR = REPO_ROOT / 'output' / 'agent-team'
EXT_DIR = REPO_ROOT / 'output' / 'agent-team-extended'
BUNDLE_DIR = REPO_ROOT / 'output' / 'interview-bundle'


def run_cmd(args: list[str]) -> None:
    subprocess.run(args, cwd=REPO_ROOT, check=True)


def must_exist(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f'Missing required artifact: {path}')


def to_repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def main() -> None:
    run_cmd(['python3', 'scripts/miro_gtm_agent_team.py'])

    for path in [
        EXT_DIR / 'run_summary.json',
        EXT_DIR / 'dependencies.json',
        EXT_DIR / '07_oss_community_pipeline.json',
        EXT_DIR / '08_benchmark_watchdog.json',
        EXT_DIR / '09_reddit_intent_radar.json',
        EXT_DIR / '10_hn_trend_radar.json',
        EXT_DIR / '11_icp_enrichment_resolver.json',
        EXT_DIR / '12_competitive_intel_synthesizer.json',
    ]:
        must_exist(path)

    run_cmd(['python3', 'scripts/render_miro_workflow_drilldown.py'])
    run_cmd(['python3', 'scripts/render_miro_full_audit_html.py'])
    run_cmd(['python3', 'scripts/render_agent_functional_map.py'])
    run_cmd(['python3', 'scripts/render_execution_provenance.py'])
    run_cmd(['python3', 'scripts/build_interview_bundle.py'])
    run_cmd(['python3', 'scripts/render_human_friendly_frontpage.py'])

    manager = json.loads((CORE_DIR / '06_manager_summary.json').read_text(encoding='utf-8'))
    ext = json.loads((EXT_DIR / 'run_summary.json').read_text(encoding='utf-8'))

    summary = {
        'portable_validation': 'pass',
        'source_csv': manager.get('source_csv'),
        'lead_input_count': manager.get('lead_input_count'),
        'accepted_count': manager.get('accepted_count'),
        'qa_approved': manager.get('qa_approved'),
        'total_agents': ext.get('total_agents'),
        'bundle_index': to_repo_rel(BUNDLE_DIR / 'index.html'),
    }
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
