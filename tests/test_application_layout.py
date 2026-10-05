"""Portable layout, guarded import and backwards-compatible source boundaries."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import application_layout as layout
from installation_migration import import_legacy
from state_store import atomic_json

ROOT=Path(__file__).resolve().parents[1]


class ApplicationLayoutTests(unittest.TestCase):
    def test_user_roots_and_relative_xdg_are_bounded(self):
        home=Path('/synthetic/home')
        self.assertEqual(layout.user_data_root('darwin',home,{}),home/'Library/Application Support/codex-model-router')
        self.assertEqual(layout.user_data_root('win32',home,{'LOCALAPPDATA':'/synthetic/local'}),Path('/synthetic/local/codex-model-router'))
        self.assertEqual(layout.user_data_root('linux',home,{'XDG_DATA_HOME':'relative'}),home/'.local/share/codex-model-router')
        self.assertEqual(layout.user_data_root('linux',home,{'XDG_DATA_HOME':'/synthetic/xdg'}),Path('/synthetic/xdg/codex-model-router'))

    def test_source_layout_and_explicit_data_override_remain_compatible(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{},clear=True):
            self.assertEqual(layout.data_root(folder),Path(folder))
            with patch.dict(os.environ,{'PERSONAL_CODEX_ROUTER_ROOT':folder+'/data'}):
                self.assertEqual(layout.data_root(ROOT),(Path(folder)/'data').resolve())

    def test_native_manifest_runtime_cannot_escape_owned_contents(self):
        with tempfile.TemporaryDirectory() as folder:
            contents=Path(folder)/'Moved.app/Contents';resources=contents/'Resources';resources.mkdir(parents=True)
            runtime=contents/'Helpers/runtime/router-runtime';runtime.parent.mkdir(parents=True);runtime.write_text('fixture')
            value={'schema':1,'layout':'macos-bundle-v1','runtime':'Helpers/runtime/router-runtime'}
            atomic_json(resources/'application.json',value)
            self.assertEqual(layout.runtime_command('desktop',resources,Path(folder)/'data'),[str(runtime.resolve()),'--data-root',str((Path(folder)/'data').resolve()),'desktop'])
            for path in ('/etc/passwd','../outside','Helpers/../../outside'):
                atomic_json(resources/'application.json',dict(value,runtime=path))
                with self.assertRaises(ValueError):layout.installed_path(resources,'runtime')
            outside=Path(folder)/'outside';outside.write_text('fixture');runtime.unlink();runtime.symlink_to(outside)
            atomic_json(resources/'application.json',value)
            with self.assertRaises(ValueError):layout.installed_path(resources,'runtime')

    def test_bootstrap_is_private_and_never_overwrites_preferences_or_unknown_config(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'data'
            self.assertTrue(layout.bootstrap(ROOT,root,'darwin'))
            config=root/'config.local.json';original=json.loads(config.read_text());original['enabled']=False;original['owner_preference']='fixture'
            config.write_text(json.dumps(original));before=config.read_bytes()
            self.assertFalse(layout.bootstrap(ROOT,root,'darwin'));self.assertEqual(config.read_bytes(),before)
            with self.assertRaises(ValueError):layout.bootstrap(ROOT,root,'linux')
            self.assertEqual(config.read_bytes(),before)
            self.assertNotIn('python',original)

    def legacy(self, root):
        atomic_json(root/'config.local.json',{'platform':sys.platform,'enabled':False,'owner_preference':'fixture'})
        (root/'state').mkdir()
        (root/'state/history.jsonl').write_text('{"fixture":true}\n')
        (root/'state/prompts.jsonl').write_text('{"synthetic":true}\n')
        atomic_json(root/'state/task-modes'/('a'*64+'.json'),{'thread':'synthetic','mode':'manual'})
        (root/'state/jev-typesafe.secret').write_bytes(b'opaque ciphertext fixture')
        (root/'state/build-fixture').mkdir();(root/'state/build-fixture/ignored').write_text('not product data')

    def test_offline_import_preserves_source_bytes_modes_and_credential_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'source';target=Path(folder)/'data';self.legacy(source)
            before={str(p.relative_to(source)):p.read_bytes() for p in source.rglob('*') if p.is_file()}
            result=import_legacy(source,target)
            self.assertTrue(result['sourcePreserved']);self.assertTrue(result['integrationPending'])
            for name,body in before.items():self.assertEqual((source/name).read_bytes(),body)
            for name in ('config.local.json','state/history.jsonl','state/prompts.jsonl','state/jev-typesafe.secret'):
                self.assertEqual((target/name).read_bytes(),before[name])
            self.assertFalse((target/'state/build-fixture').exists());self.assertFalse((target/'state/desktop-integration.json').exists())
            self.assertEqual(layout.credential_namespace(source),layout.credential_namespace(target))
            self.assertEqual(json.loads((target/'config.local.json').read_text())['enabled'],False)

    def test_import_refuses_active_bridge_existing_target_symlinks_and_cross_platform(self):
        for kind in ('active','existing','link','platform'):
            with tempfile.TemporaryDirectory() as folder:
                source=Path(folder)/'source';target=Path(folder)/'data';self.legacy(source)
                if kind=='active':atomic_json(source/'state/status-fixture.json',{'pid':os.getpid()})
                if kind=='existing':target.mkdir();(target/'owner').write_text('preserve')
                if kind=='link':(source/'state/prompts.jsonl').unlink();(source/'state/prompts.jsonl').symlink_to(source/'config.local.json')
                if kind=='platform':atomic_json(source/'config.local.json',{'platform':'foreign'})
                with self.assertRaises(ValueError):import_legacy(source,target)
                if kind=='existing':self.assertEqual((target/'owner').read_text(),'preserve')
                else:self.assertFalse(target.exists())
                self.assertEqual(list(Path(folder).glob('.router-import-*')),[])

    def test_packaged_dispatch_source_fixture_uses_explicit_root_and_does_not_register(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'data';env=dict(os.environ)
            for key in ('PERSONAL_CODEX_ROUTER_ROOT','PERSONAL_CODEX_ROUTER_CODE_ROOT','PERSONAL_CODEX_ROUTER_CONFIG','PERSONAL_CODEX_ROUTER_STATE'):env.pop(key,None)
            command=[sys.executable,str(ROOT/'packaged_main.py'),'--resources',str(ROOT),'--data-root',str(root),'bootstrap']
            first=subprocess.run(command,env=env,capture_output=True,check=True)
            second=subprocess.run(command,env=env,capture_output=True,check=True)
            self.assertTrue(json.loads(first.stdout)['createdConfig']);self.assertFalse(json.loads(second.stdout)['createdConfig'])
            self.assertFalse((root/'state/desktop-integration.json').exists())
            identity=subprocess.run(command[:-1]+['identity'],env=env,capture_output=True,check=True)
            self.assertFalse(json.loads(identity.stdout)['packaged'])
