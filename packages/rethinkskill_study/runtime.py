"""Common native execution and narrow token accounting for both study arms."""
import json
import re
from contextlib import nullcontext
from .journal import outcome_dict, restore_outcome
from .rate_limit import SharedRateLimiter


RETRYABLE_HTTP_STATUSES = {408, 409, 425, 429}
RETRYABLE_FAILURES = {'target_timeout', 'transport_error', 'response_schema_error'}


def retryable_model_failure(value):
    if value.get('status') != 'FAILED':
        return False
    kind = value.get('failure_class')
    if kind in RETRYABLE_FAILURES:
        return True
    if kind != 'provider_http_error':
        return False
    status = (value.get('process') or {}).get('http_status')
    if status is None:
        match = re.search(r'HTTP\s+(\d{3})', value.get('failure') or '')
        status = int(match.group(1)) if match else None
    return type(status) is int and (status in RETRYABLE_HTTP_STATUSES or 500 <= status <= 599)


def reusable_optimizer_response(value):
    if value.get('status') != 'COMPLETED':
        return True
    from rethinkskill.utils.serde import strict_json_loads
    try:
        proposal = strict_json_loads(value.get('response', '').strip())
    except (ValueError, TypeError):
        return False
    return (isinstance(proposal, dict) and set(proposal) == {'operation','candidate_skill','rationale'}
            and all(type(item) is str for item in proposal.values())
            and proposal['operation'] in {'add','delete','replace','noop'})


def reusable_judge_response(value, *, prompt_variant):
    from skillopt.evaluation.judge_gate import parse_judge_payload
    response = value.get('response', '')
    payload, error = parse_judge_payload(response)
    if error or not payload:
        return False
    changes = payload.get('predicted_changes')
    if (not isinstance(changes, dict) or set(changes) != {'hard', 'soft'}
            or any(type(axis) is not int or axis not in (-1, 0, 1) for axis in changes.values())):
        return False
    if prompt_variant == 'v3':
        try:
            raw = json.loads(response.strip().removeprefix('```json').removesuffix('```').strip())
        except (ValueError, TypeError):
            return False
        return (isinstance(raw, dict) and bool(raw.get('reason'))
                and raw.get('confidence') in {'low', 'medium', 'high'})
    return True


class MeteredExecutor:
    def __init__(self, executor, ledger, *, stage, model, journal=None):
        self.executor, self.ledger = executor, ledger
        self.stage, self.model = stage, model
        self.journal = journal
        self.rate_limiter = SharedRateLimiter.from_environment()

    def public_manifest(self):
        return self.executor.public_manifest()

    def execute(self, rendered, *, workspace, timeout_seconds):
        if self.journal:
            payload = {'task':rendered.task_markdown,'skill':rendered.skill_markdown,
                       'invocation':rendered.invocation,'attachments':[a.public() for a in rendered.attachments],
                       'executor':self.public_manifest(),'timeout_seconds':timeout_seconds}
            key = f'{self.stage}:{workspace.relative_to(self.journal.root)}'
            def usage_of(value):
                try:
                    return json.loads(value['raw']).get('usage')
                except (ValueError, AttributeError):
                    return None
            def invoke():
                if self.rate_limiter:
                    self.rate_limiter.wait()
                outcome=self.executor.execute(rendered,workspace=workspace,timeout_seconds=timeout_seconds)
                if (self.rate_limiter and outcome.failure_class=='provider_http_error' and
                    (outcome.process or {}).get('http_status')==429):
                    self.rate_limiter.penalize()
                return outcome_dict(outcome)
            value = self.journal.call(key,payload,
                invoke,
                stage=self.stage,model=self.model,usage_of=usage_of,
                reusable=lambda result: (not retryable_model_failure(result) and
                    (self.stage != 'optimizer' or reusable_optimizer_response(result))))
            return restore_outcome(value)
        outcome = self.executor.execute(rendered, workspace=workspace, timeout_seconds=timeout_seconds)
        try:
            usage = json.loads(outcome.raw).get('usage')
        except (ValueError, AttributeError):
            usage = None
        self.ledger.record(usage, stage=self.stage, model=self.model,
            workspace=str(workspace), attempted_calls=outcome.attempted_calls,
            completed_calls=outcome.completed_calls, failure_class=outcome.failure_class,
            error=outcome.failure or None)
        return outcome


class StudyEvaluator:
    def __init__(self, native, ledger, *, mode, final=False):
        self.native, self.ledger, self.mode, self.final = native, ledger, mode, final
        self.calls = []

    def public_manifest(self):
        return self.native.public_manifest()

    def evaluate(self, skill, *, split, round_no):
        if self.mode == 'judge' and not self.final and split != 'train':
            raise AssertionError('Judge evolution cannot execute validation or test')
        if self.final and split != 'test':
            raise AssertionError('Frozen final evaluator only executes test')
        self.calls.append({'split': split, 'round': round_no})
        component = ('seed_validation' if round_no == 0 else 'candidate_validation') if split == 'val' and not self.final else None
        with self.ledger.capture_replacement(component) if component else nullcontext():
            return self.native.evaluate(skill, split=split, round_no=round_no)

    def judge_batches(self, training):
        """Read only artifacts from the already completed training evaluation."""
        from skillopt.evaluation.evidence import public_value
        path = (self.native.output_root / training.reference.split('#sha256=')[0]).resolve()
        if not path.is_relative_to(self.native.output_root.resolve() / 'evaluations') or 'train_round_' not in str(path):
            raise ValueError('Judge evidence must come from this run training artifacts')
        allowed = {row['case_id'] for row in training.feedback}
        manifest = json.loads((path.parent/'.rethinkskill/RUN_MANIFEST.json').read_text())
        cards = []
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if row['case_id'] not in allowed:
                continue
            episode = row.get('execution', {}).get('interactive_runner', {})
            visible = {k:row.get(k) for k in ('case_id','question','response','hard','soft','reason','fail_reason')}
            if not episode:
                workspace = manifest['selection']['task_workspaces'][row['case_id']]
                visible['task_input'] = (path.parent/'tasks'/workspace/'workspace/task.md').read_text()
            if episode:
                visible['transcript'] = episode.get('transcript', [])
                visible['behavior_failure'] = episode.get('behavior_failure')
            cards.append({'id':row['case_id'], 'hard':row['hard'], 'judge_evidence':public_value(visible)})
        return [{'results':cards}]


def judge_chat(*, model, base_url, api_key, output_root, journal=None, prompt_variant='v3'):
    from openai import OpenAI
    from rethinkskill.utils.serde import atomic_write_json
    client = OpenAI(base_url=base_url, api_key=api_key, timeout=120, max_retries=0)
    rate_limiter = SharedRateLimiter.from_environment()
    counter = 0

    def call(**kwargs):
        nonlocal counter
        counter += 1
        messages = [{'role': 'system', 'content': kwargs['system']},
                    {'role': 'user', 'content': kwargs['user']}]
        path = output_root / f'judge_requests/{counter:06d}.json'
        atomic_write_json(path, {'model': model, 'messages': messages, 'status': 'started'})
        def invoke():
            if rate_limiter:
                rate_limiter.wait()
            try:
                result = client.chat.completions.create(model=model, messages=messages,
                    temperature=0, max_tokens=kwargs['max_completion_tokens'],
                    extra_body={'enable_thinking': False})
            except Exception as exc:
                if rate_limiter and getattr(exc,'status_code',None)==429:
                    rate_limiter.penalize()
                raise
            return {'response':result.choices[0].message.content or '',
                    'usage':result.usage.model_dump() if result.usage else {}}
        try:
            value = journal.call(f'judge:{counter}',{'model':model,'messages':messages,
                'max_tokens':kwargs['max_completion_tokens']},invoke,stage=kwargs.get('stage','judge_gate'),
                model=model,reusable=lambda result: reusable_judge_response(result, prompt_variant=prompt_variant)) if journal else invoke()
        except Exception as exc:
            atomic_write_json(path, {'model': model, 'messages': messages,
                                    'status': 'failed', 'error_type': type(exc).__name__})
            error = RuntimeError(type(exc).__name__)
            error.usage_recorded = journal is not None
            raise error from None
        usage = value['usage']
        response = value['response']
        atomic_write_json(path, {'model': model, 'messages': messages,
                                'status': 'completed' if reusable_judge_response(value, prompt_variant=prompt_variant) else 'invalid_response',
                                'response': response, 'usage': usage})
        return response, {**usage, '_ledger_recorded': True} if journal else usage
    return call
