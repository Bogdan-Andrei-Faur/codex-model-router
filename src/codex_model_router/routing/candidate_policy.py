"""Policy 9 candidate eligibility. Comparison does not change policy 8 routes.

Difficulty, current risk and supported reasoning effort are independent axes.
No provider calls, permissions, native compatibility changes or transcript writes.
"""
import json
import math
import re
from pathlib import Path

from codex_model_router.routing.model_catalog import CODEX_RATES, MODELS, model_label
from codex_model_router.routing.workload import intent_text, starts_new_task, resumes_work, critical_risk

VERSION = 9
CLASSES = ('mechanical', 'bounded', 'engineering', 'demanding', 'exceptional', 'critical')
MODES = ('reference', 'compare', 'validated')
INFRASTRUCTURE_ERRORS = frozenset(('rate_limited', 'usage_limit', 'quota_exceeded', 'network',
    'timeout', 'connection', 'authentication', 'forbidden', 'turn_rejected', 'interrupted',
    'activeTurnNotSteerable', 'context_window_exceeded', 'server_error'))


def mode(config):
    value = config.get('policy_mode', 'reference')
    return value if value in MODES else 'reference'


def failure_kind(error=None, checks_failed=False):
    error = error if isinstance(error, dict) else {}
    if error.get('error_type') in INFRASTRUCTURE_ERRORS or error.get('error_http_status') in (401, 403, 408, 429, 500, 502, 503, 504):
        return 'infrastructure'
    return 'external_check' if checks_failed is True else 'unknown' if error.get('error_type') else 'none'


def profile(text, attachments=None, context=None, contract=None, failure='none'):
    value = intent_text(text)
    context = context if isinstance(context,dict) else {}
    contract = dict(contract) if isinstance(contract,dict) else {}
    fresh = starts_new_task(text)
    if fresh:
        contract = {}
    risk = critical_risk(value) or bool(re.search(r'\b(?:auditor(?:ia|y) de seguridad|security audit|adversarial|pentest|explotacion de vulnerabilidades|exploit)\b', value))
    explicit_remaining = bool(re.search(r'\b(?:solo queda|unicamente falta|only remaining)\b', value))
    continuation = resumes_work(text) or bool(re.match(r'^\s*(?:sigue fallando|no funciona|mismo error|still fails|still broken)\b', value))
    uncertain_legacy = (contract.get('legacy_uncertain') is True or
                        (not contract and continuation and context.get('work_floor') == 'critical'))
    active_risk = risk or (not fresh and contract.get('risk_active') is True)
    risk_basis = ('current' if risk else 'inherited' if active_risk else
                  'legacy_uncertain' if uncertain_legacy else 'none')
    if active_risk or uncertain_legacy:
        work_class = 'critical'
    elif re.search(r'\b(?:excepcionalmente dificil|exceptionally difficult|demostracion formal|formal proof)\b', value):
        work_class = 'exceptional'
    elif re.search(r'\b(?:refactor\w*|arquitectura|architecture|concurrencia|race condition|redisen\w*|redesign|ux|debug\w*)\b', value) or (re.search(r'\b(?:investiga\w*|revis\w*|analiza\w*)\b', value) and re.search(r'\b(?:profund\w*|fall\w*|contradict\w*|varios|multiple)\b', value)):
        work_class = 'demanding'
    elif re.search(r'\b(?:integra(?!l(?:es|s)?\b)\w*|autentic\w*|authentic\w*|authoriz\w*|migraci\w*|migration|servicios|services)\b', value):
        work_class = 'engineering'
    elif re.match(r'^\s*(?:traduce|translate|ordena alfabeticamente|sort alphabetically)\b', value) or re.fullmatch(r'\s*(?:hola|gracias|thanks|ok|vale|perfecto|listo|ya esta)[.! ]*', value):
        work_class = 'mechanical'
    elif re.search(r'\b(?:extrae|extract|csv|acotad\w*|bounded|unitari\w*|unit test|pequen\w*|small|formulario existente|boton|button|un campo|una funcion|single function)\b', value):
        work_class = 'bounded'
    elif continuation and contract.get('remaining_class') in CLASSES and not explicit_remaining:
        work_class = contract['remaining_class']
    else:
        work_class = 'engineering'
    # Future checkpoints must still retain a current risk and native boundaries.
    failures = contract.get('quality_failures', 0)
    failures = failures if type(failures) is int and 0 <= failures <= 100 else 0
    if failure == 'external_check' and continuation:
        if work_class == 'bounded':
            work_class = 'engineering'
        elif work_class == 'engineering':
            work_class = 'demanding'
        elif failures >= 2 and work_class == 'demanding':
            work_class = 'exceptional'
    efforts = {'mechanical':'low', 'bounded':'high', 'engineering':'medium',
               'demanding':'xhigh', 'exceptional':'xhigh', 'critical':'xhigh'}
    effort = efforts[work_class]
    if work_class == 'engineering' and (failure == 'external_check' or re.search(r'\b(?:integra(?!l(?:es|s)?\b)\w*|autentic\w*|authentic\w*|servicios|services)\b', value)):
        effort = 'high'
    return {'candidate_policy_version': VERSION, 'work_class': work_class, 'risk_active': bool(active_risk),
            'legacy_uncertain': bool(uncertain_legacy), 'risk_basis': risk_basis, 'failure_class': failure,
            'preferred_effort': effort, 'multi_phase': bool(re.search(r'\b(?:despues|luego|then|varias fases|multi.phase)\b', value)),
            'requires_jev': work_class != 'mechanical', 'new_task': fresh}


def next_contract(previous, assessment, feedback_id=None):
    previous = previous or {}
    old = {} if assessment.get('new_task') else dict(previous)
    failures = old.get('quality_failures', 0)
    failures = failures if type(failures) is int and 0 <= failures <= 100 else 0
    if assessment['failure_class'] == 'external_check' and feedback_id and old.get('feedback_id') != feedback_id:
        failures = min(100, failures + 1)
    return {'version': VERSION, 'remaining_class': assessment['work_class'],
            # Keep the conservative floor without relabelling uncertainty as
            # observed risk on the next turn. Old risk_active contracts remain
            # conservative: their lost provenance cannot be reconstructed.
            'risk_active': assessment['risk_active'],
            'legacy_uncertain': assessment.get('legacy_uncertain', False), 'quality_failures': failures,
            'feedback_id': feedback_id or old.get('feedback_id')}


def candidates(routes, catalog, assessment):
    """Shared local/Jev eligible pairs, intersected with this native catalog."""
    cls = assessment['work_class']
    matrix = {
        'mechanical': (('simple', ('low', 'medium')),),
        'bounded': (('simple', ('high', 'xhigh')), ('complex', ('medium', 'high'))),
        'engineering': (('complex', ('medium', 'high', 'xhigh')),),
        'demanding': (('complex', ('high', 'xhigh')),),
        'exceptional': (('complex', ('xhigh',)), ('critical', ('high', 'xhigh'))),
        'critical': (('critical', ('high', 'xhigh')),),
    }
    result = {}
    for tier, efforts in matrix[cls]:
        route = routes.get(tier, {})
        model = route.get('model')
        for effort in efforts:
            if effort not in catalog.get(model, set()):
                continue
            rates = CODEX_RATES.get(model)
            price = '' if rates is None else ' Standard créditos/M entrada/caché/salida: %s/%s/%s; coste por tarea no medido.' % rates
            key = '%s_%s' % (model.replace('.', '_').replace('-', '_'), effort)
            result[key] = {'model':model, 'effort':effort, 'tier':tier,
                'label':'%s · %s' % (model_label(model), effort),
                'description':'Alcance %s; esfuerzo %s. %s.%s' % (cls, effort,
                    {'simple':'Luna: trabajo enfocado y verificable', 'complex':'Sol: ingeniería habitual y compleja',
                     'critical':'Astra: dificultad excepcional o riesgo actual'}[tier], price)}
    return result


def local_route(assessment, choices):
    tier = {'mechanical':'simple', 'bounded':'simple', 'engineering':'complex',
            'demanding':'complex', 'exceptional':'critical', 'critical':'critical'}[assessment['work_class']]
    # Avoid starting multi-phase engineering in Luna when its next family is blocked.
    if assessment['work_class'] == 'bounded' and assessment.get('multi_phase'):
        tier = 'complex'
    preferred = assessment['preferred_effort']
    if tier == 'complex' and assessment['work_class'] == 'bounded':
        preferred = 'medium'
    eligible = [r for r in choices.values() if r['tier'] == tier]
    match = next((r for r in eligible if r['effort'] == preferred), None)
    return match or (eligible[-1] if eligible else next(iter(choices.values()), None))


def accepted_jev(result, settings):
    """No universal threshold: candidate Jev stays local until calibrated."""
    threshold = settings.get('candidate_confidence_threshold')
    confidence = result.get('confidence')
    valid = lambda v: type(v) in (float, int) and math.isfinite(v) and 0 <= v <= 1
    return bool(result.get('status') == 'ok' and result.get('route') and valid(threshold)
                and valid(confidence) and confidence >= threshold)


def enabled_classes(config, state_dir, router_build):
    """Activation receipts bind evidence to exact candidate implementation."""
    if mode(config) != 'validated':
        return set()
    try:
        receipt = json.loads((Path(state_dir) / 'policy-validation.json').read_text())
    except (OSError, ValueError, TypeError):
        return set()
    if not isinstance(receipt, dict) or receipt.get('candidate_policy_version') != VERSION or receipt.get('router_build_id') != router_build or receipt.get('quality_source') != 'executed_fixture_checks':
        return set()
    requested = config.get('policy_classes', [])
    if not isinstance(requested, list):
        return set()
    classes = receipt.get('classes', {})
    if not isinstance(classes, dict):
        return set()
    result = set()
    for cls in requested:
        if type(cls) is not str or cls not in CLASSES:
            continue
        row = classes.get(cls)
        if cls not in CLASSES or not isinstance(row, dict):
            continue
        if (type(row.get('held_out_pairs')) is int and row['held_out_pairs'] >= 2
                and type(row.get('quality_regressions')) is int and row['quality_regressions'] == 0 and row.get('candidate_all_checks_passed') is True
                and row.get('consumption_coverage_complete') is True and row.get('lower_consumption_per_success') is True):
            result.add(cls)
    return result
