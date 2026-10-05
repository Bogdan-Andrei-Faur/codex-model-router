"""Read-only synthetic routing review: eligibility is not demonstrated quality.

No provider requests or private conversation data. Recommendations are explicit
review labels for future matched experiments, not an activated routing policy.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from routing import DEFAULT_ROUTES, EFFORTS, select_route_details
from decision_engines import candidate_routes
from model_catalog import CODEX_RATES
from build_identity import POLICY_VERSION


CASES = (
    ('bounded_text', 'Traduce al inglés: hola', False, 'simple', 'low'),
    ('small_verified_edit', 'Añade un campo obligatorio al formulario existente con su prueba unitaria.', False, 'simple', 'high'),
    ('bounded_tests', 'Ejecuta la prueba unitaria del módulo de fechas y comunica si pasa.', False, 'simple', 'high'),
    ('routine_auth', 'Configure authentication for the application.', False, 'complex', 'high'),
    ('ambiguous_followup', 'Tengo una duda sobre esto.', False, 'complex', 'medium'),
    ('deep_bounded_debug', 'Investiga con una revisión profunda por qué falla una prueba unitaria del módulo de fechas.', False, 'complex', 'xhigh'),
    ('complete_bounded_refactor', 'Refactoriza por completo el módulo de fechas; conserva su contrato y ejecuta las pruebas.', False, 'complex', 'xhigh'),
    ('bounded_accessibility', 'Revisa la accesibilidad de este botón con criterios comprobables.', False, 'complex', 'high'),
    ('attachment_csv', 'Extrae las cifras de la tabla CSV adjunta.', True, 'simple', 'high'),
    ('broad_visual_design', 'Rediseña toda la UX de la aplicación.', False, 'complex', 'xhigh'),
    ('security_audit', 'Audita los permisos del servicio para detectar vulnerabilidades.', False, 'critical', 'xhigh'),
    ('production_data_loss', 'Investiga la pérdida de datos en producción.', False, 'critical', 'xhigh'),
)


def evaluate():
    catalog = {r['model']: set(EFFORTS) - {'ultra'} for r in DEFAULT_ROUTES.values()}
    results = []
    for code, text, attachments, recommendation, effort in CASES:
        route, policy = select_route_details(text, DEFAULT_ROUTES, attachments=attachments)
        candidates = candidate_routes(DEFAULT_ROUTES, catalog, policy)
        proposed = DEFAULT_ROUTES[recommendation]['model']
        results.append({'case':code, 'local_model':route['model'], 'local_effort':route['effort'],
                        'quality_floor':policy['quality_floor'], 'quality_ceiling':policy['quality_ceiling'],
                        'jev_eligible_models':sorted({r['model'] for r in candidates.values()}),
                        'recommended_trial_model':proposed, 'recommended_trial_effort':effort,
                        'trial_currently_eligible':any(r['model'] == proposed and r['effort'] == effort for r in candidates.values())})
    # Fixed token volumes illustrate relative rates, never predict actual usage.
    rates = {m: {'input':v[0], 'cached_input':v[1], 'output':v[2]} for m,v in CODEX_RATES.items() if m in {r['model'] for r in DEFAULT_ROUTES.values()}}
    return {'policy_version':POLICY_VERSION, 'synthetic_cases':len(results), 'provider_calls':0,
            'actual_jev_choices_measured':False, 'quality_measured':False,
            'causal_savings_demonstrated':False, 'standard_credits_per_million_tokens':rates,
            'limitations':['Recommendations require matched executed checks before activation.',
                           'Local candidate eligibility constrains JEV, but does not measure its independent judgment.',
                           'Reasoning effort changes token volumes; rates alone cannot predict task cost.'], 'cases':results}


if __name__ == '__main__':
    print(json.dumps(evaluate(),indent=2))
