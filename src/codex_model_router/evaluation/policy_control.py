"""Reversible policy selection. Validated categories require matching evidence."""
import argparse
import json
from pathlib import Path
from codex_model_router.paths import resource_root
import codex_model_router.routing.candidate_policy as cp
from codex_model_router.build_identity import router_identity
from codex_model_router.storage.state_store import file_lock, atomic_json


def configure(root, selection, classes=None):
    root=Path(root)
    if selection not in cp.MODES or (classes is not None and (not isinstance(classes,list) or
            not all(type(c) is str and c in cp.CLASSES for c in classes) or len(set(classes))!=len(classes))):
        raise ValueError('invalid_policy_selection')
    with file_lock(root/'state'/'config.lock'):
        path=root/'config.local.json'
        config=json.loads(path.read_text(encoding='utf-8-sig'))
        updated=dict(config,policy_mode=selection)
        if classes is not None:updated['policy_classes']=classes
        if selection=='validated':
            requested=updated.get('policy_classes',[])
            if not requested or set(requested)!=cp.enabled_classes(updated,root/'state',router_identity(root)):
                raise ValueError('matching_quality_consumption_evidence_required')
        updated.setdefault('candidate_jev_comparison',False)
        atomic_json(path,updated)
    return status(root)


def status(root):
    root=Path(root); config=json.loads((root/'config.local.json').read_text(encoding='utf-8-sig'))
    return {'policy_mode':cp.mode(config),'reference_policy_version':8,'candidate_policy_version':cp.VERSION,
        'activated_classes':sorted(cp.enabled_classes(config,root/'state',router_identity(root))),
        'candidate_jev_comparison':config.get('candidate_jev_comparison') is True,
        'comparison_is_quality_proof':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('status','reference','compare','validated'))
    p.add_argument('--root',type=Path,default=resource_root())
    p.add_argument('--class',dest='classes',action='append',choices=cp.CLASSES)
    args=p.parse_args()
    try:
        result=status(args.root) if args.action=='status' else configure(args.root,args.action,args.classes)
        print(json.dumps(result,indent=2))
    except (OSError,ValueError,TypeError):
        p.exit(1,'Policy selection failed; current configuration preserved. Check matching evidence.\n')


if __name__=='__main__':main()
