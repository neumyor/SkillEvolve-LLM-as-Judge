import json
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import run_rethinkskill_full as supervisor


def test_supervisor_classifies_recovery_and_audit_failures(tmp_path, monkeypatch):
    out=tmp_path/'run'
    out.mkdir()
    assert supervisor.classify_run(out,1)[:2]==('retryable','missing_summary')
    assert supervisor.classify_run(out,-15)[:2]==('interrupted','signal_15')
    (out/'summary.json').write_text(json.dumps({'status':'invalid',
        'failure_class':'provider_http_error','failure':'HTTP 500'}))
    assert supervisor.classify_run(out,1)[:2]==('retryable','provider_http_error')
    (out/'summary.json').write_text(json.dumps({'status':'invalid',
        'failure_class':'optimizer_response_schema_error'}))
    assert supervisor.classify_run(out,1)[0]=='retryable'
    (out/'summary.json').write_text(json.dumps({'status':'invalid',
        'failure_class':'optimizer_response_contract_error'}))
    assert supervisor.classify_run(out,1)[0]=='permanent_failure'
    (out/'summary.json').write_text(json.dumps({'status':'completed'}))
    monkeypatch.setattr(supervisor,'audit_run',lambda root:['Tampered result'])
    assert supervisor.classify_run(out,0)==('integrity_error','audit_failed',['Tampered result'])
    monkeypatch.setattr(supervisor,'audit_run',lambda root:[])
    assert supervisor.classify_run(out,0)[0]=='completed'


def test_pending_tasks_reports_failure_and_missing_result(tmp_path):
    out=tmp_path/'run'
    evaluation=out/'runs/evolution/evaluations/val_round_0000'
    manifest=evaluation/'.rethinkskill/RUN_MANIFEST.json'
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({'selection':{'task_workspaces':{
        'ok':'task-ok','bad':'task-bad','missing':'task-missing'}}}))
    for name, failure in (('ok',None),('bad','provider_http_error')):
        path=evaluation/'tasks'/f'task-{name}'/'RESULT.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'failure_class':failure}))
    pending=supervisor.pending_tasks(out)
    assert [(row['case_id'],row['failure_class']) for row in pending]==[
        ('bad','provider_http_error'),('missing','missing_result')]


def test_full_run_rejects_preflight_from_another_endpoint(tmp_path, monkeypatch):
    preflight = tmp_path / 'preflight'
    preflight.mkdir()
    names = [f'{benchmark}_{mode}' for benchmark in ('searchqa', 'alfworld')
             for mode in ('baseline', 'judge')]
    (preflight / 'verification.json').write_text(json.dumps({
        name: {'status': 'passed'} for name in names}))
    (preflight / 'plan.json').write_text(json.dumps({'max_requests_per_minute': 24}))
    monkeypatch.setattr(supervisor, 'audit_run', lambda _path: [])
    monkeypatch.setattr(supervisor, 'load_local_config', lambda: {
        'searchqa-eval': {'base_url': 'https://current.example/v1'},
        'alfworld-eval': {'base_url': 'https://current.example/v1'},
    })
    for name in names:
        run = preflight / name
        run.mkdir()
        (run / 'implementation.json').write_text('{}')
        (run / 'study_manifest.json').write_text(json.dumps({
            'model': 'qwen3.6-flash-distill', 'judge_model': 'qwen3.6-flash-distill',
            'judge_prompt_variant': 'v3', 'base_url': 'https://previous.example/v1',
        }))
    monkeypatch.setattr(sys, 'argv', ['run_rethinkskill_full.py', '--root',
        str(tmp_path / 'full'), '--preflight', str(preflight)])
    with pytest.raises(ValueError, match='Preflight endpoint differs'):
        supervisor.main()
