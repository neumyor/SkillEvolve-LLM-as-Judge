import json
import pytest
from test_rethinkskill_study import args_for, Executor, proposal, decision
from rethinkskill_study.runner import run
from rethinkskill_study.audit import audit_run
from rethinkskill.runtime.types import ModelOutcome
from rethinkskill_study.journal import DurableLedger, RequestJournal
from rethinkskill_study.runtime import retryable_model_failure, reusable_judge_response, reusable_optimizer_response

class Interrupted(Executor):
    def execute(self, rendered, **kw):
        if len(self.tasks)==2:
            raise KeyboardInterrupt()
        return super().execute(rendered, **kw)


def test_resume_reuses_requests_and_refuses_drift(tmp_path):
    args=args_for(tmp_path,'baseline')
    target=Interrupted(['<answer>wrong</answer>']*2)
    with pytest.raises(KeyboardInterrupt):
        run(args,target_executor=target,optimizer_executor=Executor([proposal()]))
    args.resume=True
    target=Executor(['<answer>New York</answer>']*2)
    opt=Executor([])
    assert run(args,target_executor=target,optimizer_executor=opt)==0
    assert len(target.tasks)==2 and not opt.tasks
    assert audit_run(args.output_dir)==[]
    cost=json.loads((args.output_dir/'replacement_cost.json').read_text())
    assert cost['total_tokens']==24
    assert not cost['usage_complete'] # interrupted in-flight candidate request remains unknown
    assert run(args,target_executor=Executor([]),optimizer_executor=Executor([]))==0
    args.rounds=2
    with pytest.raises(ValueError,match='changed implementation or controls'):
        run(args,target_executor=Executor([]),optimizer_executor=Executor([]))

class Failed(Executor):
    def execute(self,rendered,**kw):
        self.tasks.append(rendered)
        return ModelOutcome(status='FAILED',response='',raw='',process={'returncode':1},
            attempted_calls=1,completed_calls=0,failure_class='provider_http_error',failure='HTTP 500: internal error')


@pytest.mark.parametrize('workers', [1, 2])
def test_http500_invalidates_official_evolution_without_final_test(tmp_path, workers):
    args=args_for(tmp_path,'baseline')
    args.workers=workers
    for split in ('train','val','test'):
        p=getattr(args,split+'_items');rows=json.loads(p.read_text());rows.append({**rows[0],'id':split+'2'});p.write_text(json.dumps(rows))
    target=Failed([])
    assert run(args,target_executor=target,optimizer_executor=Executor([proposal()]))==1
    assert len(target.tasks)==2
    assert not (args.output_dir/'test_summary.json').exists()
    receipt=json.loads((args.output_dir/'evolution_receipt.json').read_text())
    assert receipt['status']=='RETHINKSKILL_EVOLUTION_INVALID'
    assert receipt['target_calls']['completed']==0
    cost=json.loads((args.output_dir/'replacement_cost.json').read_text())
    assert not cost['usage_complete']
    assert json.loads((args.output_dir/'summary.json').read_text())['status']=='invalid'


def test_journal_recovers_usage_write_gap_and_deduplicates(tmp_path):
    ledger=DurableLedger(tmp_path/'usage_events.jsonl');ledger.configure_replacement_cost('rethinkskill','judge')
    j=RequestJournal(tmp_path,ledger)
    with ledger.capture_replacement('llm_judge'):
        j.call('a',{},lambda:{'usage':{'prompt_tokens':4,'completion_tokens':2}},stage='judge',model='test')
    (tmp_path/'usage_events.jsonl').write_text('')
    ledger=DurableLedger(tmp_path/'usage_events.jsonl');ledger.configure_replacement_cost('rethinkskill','judge')
    j=RequestJournal(tmp_path,ledger)
    j.call('a',{},lambda:pytest.fail('must not repeat'),stage='judge',model='test')
    assert len(ledger.events())==1
    assert json.loads((tmp_path/'replacement_cost.json').read_text())['total_tokens']==6


@pytest.mark.parametrize('status,expected', [(400,False),(408,True),(429,True),(500,True),(503,True)])
def test_only_transient_http_failures_are_retryable(status, expected):
    assert retryable_model_failure({'status':'FAILED','failure_class':'provider_http_error',
        'process':{'http_status':status},'failure':f'HTTP {status}'}) is expected


def test_journal_retries_legacy_cached_failure_but_reuses_success(tmp_path):
    ledger=DurableLedger(tmp_path/'usage_events.jsonl')
    ledger.configure_replacement_cost('rethinkskill','baseline')
    journal=RequestJournal(tmp_path,ledger)
    failure={'status':'FAILED','failure_class':'provider_http_error',
             'process':{'http_status':500},'failure':'HTTP 500','usage':None}
    success={'status':'COMPLETED','failure_class':None,'process':{},'failure':'',
             'usage':{'prompt_tokens':4,'completion_tokens':2}}
    # Simulate a failure cached by the older journal implementation.
    journal.call('task',{},lambda:failure,stage='target',model='test')
    ledger=DurableLedger(tmp_path/'usage_events.jsonl')
    journal=RequestJournal(tmp_path,ledger)
    calls=[]
    reusable=lambda value:not retryable_model_failure(value)
    with ledger.capture_replacement('candidate_validation'):
        result=journal.call('task',{},lambda:calls.append(1) or success,
                            stage='target',model='test',reusable=reusable)
        again=journal.call('task',{},lambda:pytest.fail('successful task must be reused'),
                           stage='target',model='test',reusable=reusable)
    assert result==again==success and len(calls)==1
    assert len(ledger.events())==2


def test_resume_reexecutes_only_failed_searchqa_task(tmp_path):
    args=args_for(tmp_path,'baseline')
    args.workers=2
    rows=json.loads(args.val_items.read_text())
    rows.append({**rows[0],'id':'val2','question':'Second city?'})
    args.val_items.write_text(json.dumps(rows))
    class OneFailure(Executor):
        def execute(self,rendered,**kw):
            self.tasks.append(rendered)
            if 'Second city?' in rendered.task_markdown:
                return ModelOutcome(status='FAILED',response='',raw='',process={'http_status':500},
                    attempted_calls=1,completed_calls=0,failure_class='provider_http_error',failure='HTTP 500')
            return ModelOutcome(status='COMPLETED',response='<answer>wrong</answer>',
                raw=json.dumps({'usage':{'prompt_tokens':10,'completion_tokens':2}}),process={},
                attempted_calls=1,completed_calls=1)
    first=OneFailure([])
    assert run(args,target_executor=first,optimizer_executor=Executor([proposal()]))==1
    assert len(first.tasks)==2
    args.resume=True
    args.workers=1
    second=Executor(['<answer>wrong</answer>']*5)
    assert run(args,target_executor=second,optimizer_executor=Executor([proposal()]))==0
    assert len(second.tasks)==5
    assert sum('Second city?' in task.task_markdown for task in second.tasks)==2
    assert audit_run(args.output_dir)==[]
    assert len(list((args.output_dir/'recovery').iterdir()))==1
    manifest=json.loads((args.output_dir/'study_manifest.json').read_text())
    assert manifest['actual_concurrency']==1 and manifest['concurrency_ceiling']==2


def test_invalid_judge_reply_is_not_replayed_after_resume(tmp_path, monkeypatch):
    import openai
    from types import SimpleNamespace as NS
    replies=iter(['not json','still not json',decision()])
    calls=[]
    def create(**kwargs):
        calls.append(kwargs)
        return NS(choices=[NS(message=NS(content=next(replies)))],
                  usage=NS(model_dump=lambda:{'prompt_tokens':5,'completion_tokens':2}))
    monkeypatch.setattr(openai,'OpenAI',lambda **kw:NS(chat=NS(completions=NS(create=create))))
    args=args_for(tmp_path,'judge')
    assert run(args,target_executor=Executor(['<answer>wrong</answer>']),
               optimizer_executor=Executor([proposal()]))==1
    args.resume=True
    assert run(args,target_executor=Executor(['<answer>New York</answer>']),
               optimizer_executor=Executor([]))==0
    assert len(calls)==3
    assert audit_run(args.output_dir)==[]
    assert json.loads((args.output_dir/'replacement_cost.json').read_text())['total_tokens']==21


def test_judge_cache_requires_complete_decision():
    assert not reusable_judge_response({'response':'{"verdict":"ACCEPT"}'},prompt_variant='v3')
    assert reusable_judge_response({'response':decision()},prompt_variant='v3')


def test_malformed_optimizer_reply_retries_without_relaxing_official_parser(tmp_path):
    assert not reusable_optimizer_response({'status':'COMPLETED',
        'response':'```json\n'+proposal()+'\n```'})
    args=args_for(tmp_path,'baseline')
    assert run(args,target_executor=Executor(['<answer>wrong</answer>']*2),
               optimizer_executor=Executor(['```json\n'+proposal()+'\n```']))==1
    assert json.loads((args.output_dir/'summary.json').read_text())['failure_class']=='optimizer_response_schema_error'
    args.resume=True
    target=Executor(['<answer>wrong</answer>','<answer>New York</answer>'])
    optimizer=Executor([proposal()])
    assert run(args,target_executor=target,optimizer_executor=optimizer)==0
    assert len(target.tasks)==2 and len(optimizer.tasks)==1
    assert audit_run(args.output_dir)==[]


def test_judge_resume_uses_journal_and_keeps_cost(tmp_path, monkeypatch):
    import openai
    from types import SimpleNamespace as NS
    calls=[]
    def create(**kw):
        calls.append(kw)
        return NS(choices=[NS(message=NS(content=decision()))],usage=NS(model_dump=lambda:{'prompt_tokens':5,'completion_tokens':2}))
    monkeypatch.setattr(openai,'OpenAI',lambda **kw:NS(chat=NS(completions=NS(create=create))))
    args=args_for(tmp_path,'judge')
    class StopFinal(Executor):
        def execute(self,rendered,**kw):
            if self.tasks: raise KeyboardInterrupt()
            return super().execute(rendered,**kw)
    with pytest.raises(KeyboardInterrupt):
        run(args,target_executor=StopFinal(['<answer>wrong</answer>']),optimizer_executor=Executor([proposal()]))
    args.resume=True
    target=Executor(['<answer>New York</answer>'])
    assert run(args,target_executor=target,optimizer_executor=Executor([]))==0
    assert len(calls)==1 and len(target.tasks)==1
    assert audit_run(args.output_dir)==[]
    cost=json.loads((args.output_dir/'replacement_cost.json').read_text())
    assert cost['total_tokens']==7 and cost['usage_complete']
    assert calls[0]['messages'][0]['role']=='system'


@pytest.mark.parametrize("failure_class,reason", [("target_timeout","timed out"),("provider_http_error","HTTP 502: failed")])
def test_other_failures_are_not_silently_scored(tmp_path,failure_class,reason):
    class OtherFailure(Failed):
        def execute(self,rendered,**kw):
            self.tasks.append(rendered)
            return ModelOutcome(status='FAILED',response='',raw='',process={'returncode':1},
                attempted_calls=1,completed_calls=0,failure_class=failure_class,failure=reason)
    args=args_for(tmp_path,'baseline')
    assert run(args,target_executor=OtherFailure([]),optimizer_executor=Executor([]))==1
    assert not (args.output_dir/'test_summary.json').exists()


def test_parallel_native_tasks_publish_in_original_order(tmp_path):
    args=args_for(tmp_path,'baseline'); args.workers=3
    target=Executor(['<answer>wrong</answer>','<answer>wrong</answer>','<answer>New York</answer>','<answer>New York</answer>'])
    assert run(args,target_executor=target,optimizer_executor=Executor([proposal()]))==0
    ev=tmp_path/'baseline/runs/evolution/evaluations/val_round_0000/results.jsonl'
    ids=[json.loads(x)['case_id'] for x in ev.read_text().splitlines()]
    assert ids==['val1']
    manifest=json.loads((tmp_path/'baseline/study_manifest.json').read_text())
    assert manifest['actual_concurrency']==3


def test_parallel_native_tasks_publish_before_slowest_task_finishes(tmp_path):
    import time
    args=args_for(tmp_path,'baseline');args.workers=2
    rows=json.loads(args.val_items.read_text())
    rows.append({**rows[0],'id':'val2','question':'Second city?'})
    args.val_items.write_text(json.dumps(rows))
    val_root=tmp_path/'baseline/runs/evolution/evaluations/val_round_0000'
    class Probe:
        observed_early_result=False
        def public_manifest(self):return {'kind':'probe'}
        def execute(self,rendered,**kw):
            if 'Second city?' in rendered.task_markdown:
                deadline=time.monotonic()+2
                while time.monotonic()<deadline and not list((val_root/'tasks').rglob('RESULT.json')):
                    time.sleep(.005)
                self.observed_early_result=bool(list((val_root/'tasks').rglob('RESULT.json')))
            return ModelOutcome(status='COMPLETED',response='<answer>wrong</answer>',raw='',
                process={},attempted_calls=1,completed_calls=1)
    target=Probe()
    assert run(args,target_executor=target,optimizer_executor=Executor(['not JSON']))==1
    assert target.observed_early_result
    assert len(list((val_root/'tasks').rglob('RESULT.json')))==2
