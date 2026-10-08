"""Bounded regressions for the four October 2026 security findings."""
from tests.grader_sandbox import INTEGRATION, run_sandbox
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
import codex_model_router.telemetry.evidence as evidence
import codex_model_router.storage.state_store as state_store
from codex_model_router.platforms.platform_support import TELEMETRY_AUTH_ENV, with_loopback_telemetry
from codex_model_router.bridge.router import Router
from codex_model_router.storage.recover_history import recover
from tests.coding_trials import SandboxUnavailable, require_memory_result


@unittest.skipIf(os.name == 'nt', 'POSIX owner-only permission boundary')
class PrivateStateTests(unittest.TestCase):
    def test_first_write_and_existing_append_are_private_under_open_umask(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); state = root/'state'; old = os.umask(0)
            observed = []
            real_open = state_store.private_open
            def before_write(path, *args, **kwargs):
                stream = real_open(path, *args, **kwargs)
                observed.append(stat.S_IMODE(os.fstat(stream.fileno()).st_mode))
                self.assertEqual(observed[-1], 0o600)
                return stream
            try:
                state.mkdir(mode=0o777)
                existing = state/'prompts.jsonl'; existing.write_text('partial')
                existing.chmod(0o666)
                with patch.object(state_store, 'private_open', side_effect=before_write):
                    state_store.append_prompt_record(state, {'prompt':'synthetic', 'time':time.time()})
                    state_store.append_record(state, {'time':time.time(), 'decision_id':'test'})
                    state_store.compact_history(state, 1)
                    state_store.compact_prompt_history(state, 1)
                    state_store.atomic_json(state/'workloads'/'test.json', {'synthetic':True})
                self.assertTrue(observed)
                self.assertEqual(stat.S_IMODE(state.stat().st_mode), 0o700)
                for name in ('prompts.jsonl','history.jsonl','workloads/test.json'):
                    self.assertEqual(stat.S_IMODE((state/name).stat().st_mode), 0o600)
                self.assertIn('synthetic',existing.read_text())
            finally:
                os.umask(old)

    def test_status_and_recovery_files_are_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); config = root/'config.json'; config.write_text('{}')
            old = os.umask(0)
            try:
                router = Router(config, root/'state'); router.log({'event':'synthetic'})
                status = next((root/'state').glob('status-*.json'))
                self.assertEqual(stat.S_IMODE(status.stat().st_mode), 0o600)
                source = root/'snapshot.json'
                source.write_text(json.dumps({'events':[{'event':'turn_accepted','thread':'synthetic',
                    'time':'2026-10-01T00:00:00Z'}]}))
                out = root/'recovered.jsonl'; self.assertEqual(recover(source,out),1)
                self.assertEqual(stat.S_IMODE(out.stat().st_mode), 0o600)
                self.assertEqual(recover(source,out),0)
            finally:
                os.umask(old)

    def test_append_refuses_links_without_overwriting_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); target = root/'owned'; target.write_text('preserve')
            link = root/'link'; link.symlink_to(target)
            with self.assertRaises(OSError):
                state_store.private_open(link, 'w')
            hard = root/'hard'; os.link(target,hard)
            with self.assertRaises(OSError):
                state_store.private_open(hard,'w')
            self.assertEqual(target.read_text(),'preserve')

    def test_generic_lock_preserves_shared_parent_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent=Path(tmp);parent.chmod(0o755)
            with state_store.file_lock(parent/'.router-import.lock'):
                self.assertEqual(stat.S_IMODE(parent.stat().st_mode),0o755)
            self.assertEqual(stat.S_IMODE((parent/'.router-import.lock').stat().st_mode),0o600)


class TelemetryTransportTests(unittest.TestCase):
    def test_secret_only_in_child_environment_in_all_native_layouts(self):
        token = 'synthetic-secret-not-an-account-key'
        for args in (['app-server'], ['-c','model="test"','app-server'],
                     ['app-server','-c','model="test"']):
            for traces in (False,True):
                env={'existing':'preserved'}
                command=with_loopback_telemetry(args,'http://127.0.0.1:4321/v1/logs',token,env=env,traces=traces)
                self.assertEqual(command[:len(args)],args)
                self.assertNotIn(token,' '.join(command))
                self.assertNotIn('Authorization',' '.join(command))
                self.assertEqual(env[TELEMETRY_AUTH_ENV],'Authorization=Bearer '+token)
                if traces:
                    self.assertEqual(env['OTEL_EXPORTER_OTLP_TRACES_HEADERS'],env[TELEMETRY_AUTH_ENV])
                self.assertEqual(env['existing'],'preserved')
        with self.assertRaisesRegex(ValueError,'private_telemetry_environment_required'):
            with_loopback_telemetry(['app-server'],'http://127.0.0.1',token)


class EvidenceLimitTests(unittest.TestCase):
    def run_zip(self, members, limits, expected):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source=root/'in.zip'; output=root/'out.zip'
            with ZipFile(source,'w',ZIP_DEFLATED) as z:
                for name,value in members:
                    z.writestr(name,value)
            with patch.multiple(evidence,**limits), self.assertRaisesRegex(ValueError,expected):
                evidence.export(source,output)
            self.assertFalse(output.exists())

    def test_many_members_and_aggregate_bytes_are_rejected(self):
        self.run_zip([('x%d/data/history.jsonl'%i,'{}\n') for i in range(4)],
                     {'MAX_MEMBERS':3},'evidence_budget_exceeded')
        # Compressed bytes stay below the cap; decoded bytes exceed it.
        self.run_zip([('data/history.jsonl','{}\n'*2000)],
                     {'MAX_TOTAL_BYTES':1000},'evidence_budget_exceeded')

    def test_empty_invalid_and_duplicate_lines_cannot_bypass_record_budget(self):
        for body in ('{}\n'*4, '\n'*4, 'broken\n'*4,
                     (json.dumps({'event':'decision_created','time':1})+'\n')*4):
            self.run_zip([('data/bridge_snapshots.jsonl',body)],
                         {'MAX_LINES':3},'evidence_budget_exceeded')

    def test_line_json_array_and_retained_snapshot_limits(self):
        self.run_zip([('data/history.jsonl',' '*100)],{'MAX_LINE':64},'evidence_line_too_large')
        self.run_zip([('snapshots.json',json.dumps([{}]*4))],{'MAX_SNAPSHOTS':3},'evidence_budget_exceeded')
        self.run_zip([('snapshots.json',' '*100)],{'MAX_JSON':64},'evidence_json_too_large')
        self.run_zip([('data/bridge_snapshots.jsonl',(json.dumps({'stats':{'requests':1}})+'\n')*4)],
                     {'MAX_SNAPSHOTS':3},'evidence_budget_exceeded')

    def test_retained_history_and_serialized_output_limits(self):
        body=''.join(json.dumps({'event':'decision_created','decision_id':str(i),'time':1})+'\n' for i in range(3))
        self.run_zip([('data/history.jsonl',body)],{'MAX_RECORDS':2},'evidence_budget_exceeded')
        self.run_zip([('data/history.jsonl',body)],{'MAX_OUTPUT':16},'evidence_budget_exceeded')

    def test_directory_limits_and_normal_reexport(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); state=root/'state';state.mkdir()
            (state/'history.jsonl').write_text('\n'*4)
            out=root/'out.zip'
            with patch.object(evidence,'MAX_LINES',3),self.assertRaisesRegex(ValueError,'evidence_budget_exceeded'):
                evidence.export(state,out)
            self.assertFalse(out.exists())
            (state/'history.jsonl').write_text(json.dumps({'event':'decision_created','decision_id':'synthetic','time':1})+'\n')
            summary=evidence.export(state,out)
            self.assertEqual(summary['created_decisions'],1)
            self.assertEqual(evidence.export(out,root/'again.zip')['created_decisions'],1)

    def test_zip64_cannot_override_the_preparse_metadata_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source=root/'zip64.zip';out=root/'out.zip'
            with ZipFile(source,'w') as z:
                z.writestr('events.jsonl','')
            data=source.read_bytes();end=data.rfind(b'PK\x05\x06')
            fields=struct.unpack_from('<4s4H2LH',data,end)
            directory_size,directory_offset=fields[5:7]
            record=struct.pack('<4sQ2H2L4Q',b'PK\x06\x06',44,45,45,0,0,1,1,directory_size,directory_offset)
            locator=struct.pack('<4sLQL',b'PK\x06\x07',0,end,1)
            source.write_bytes(data[:end]+record+locator+data[end:])
            with self.assertRaisesRegex(ValueError,'zip64_evidence_not_supported'):
                evidence.export(source,out)
            self.assertFalse(out.exists())

    def test_successful_snapshot_export_is_always_reimportable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'snapshots.zip';out=root/'out.zip'
            with ZipFile(source,'w',ZIP_DEFLATED) as z:
                z.writestr('data/bridge_snapshots.jsonl',
                    (json.dumps({'heartbeat':1,'stats':{'requests':1}})+'\n')*10000)
            evidence.export(source,out)
            evidence.export(out,root/'again.zip')
            with ZipFile(out) as z:
                self.assertLessEqual(len(z.read('snapshots.json')),evidence.MAX_JSON)
            with patch.object(evidence,'MAX_JSON',64),self.assertRaisesRegex(ValueError,'evidence_json_too_large'):
                evidence.export(source,root/'too-large.zip')
            self.assertFalse((root/'too-large.zip').exists())


class GraderLimitTests(unittest.TestCase):
    def test_missing_memory_capability_is_explicit_and_stops_candidate(self):
        with self.assertRaisesRegex(SandboxUnavailable,'hard_grader_memory_budget_unavailable'):
            require_memory_result(subprocess.CompletedProcess([],78))
        with self.assertRaisesRegex(SandboxUnavailable,'hard_grader_memory_budget_unavailable:set_limit$'):
            require_memory_result(subprocess.CompletedProcess([],78,stderr=b'grader_memory_guard: {"phase":"set_limit","reason":"private text"}'))
        with self.assertRaisesRegex(SandboxUnavailable,'hard_grader_memory_budget_unavailable$'):
            require_memory_result(subprocess.CompletedProcess([],78,stderr=b'grader_memory_guard: {"phase":"private text"}'))
        if os.name == 'nt':
            return
        from tests import grader_limits
        with patch.object(grader_limits,'enforce_memory_budget',return_value=False),patch.object(grader_limits.runpy,'run_path') as run:
            self.assertEqual(grader_limits.main(),78)
            run.assert_not_called()

    @unittest.skipIf(os.name == 'nt', 'POSIX quota validation')
    def test_guard_diagnoses_rejected_limit_and_requires_positive_probe(self):
        from tests import grader_limits as limits
        with patch.object(limits.resource,'setrlimit',side_effect=ValueError('private detail')):
            self.assertEqual(limits.memory_budget_status(),
                             {'verified':False,'phase':'set_limit','reason':'ValueError'})
        with patch.object(limits.resource,'setrlimit'),patch.object(limits.resource,'getrlimit',return_value=(limits.MEMORY_BYTES,limits.MEMORY_BYTES)):
            for code,body in ((0,b'{}'),(91,b'{"phase":"mmap","reason":"allocation_failed_for_other_reason"}'),
                              (-9,b''),(0,b'[]')):
                with patch.object(limits.subprocess,'run',return_value=subprocess.CompletedProcess([],code,body)):
                    self.assertFalse(limits.memory_budget_status()['verified'])

    @unittest.skipUnless(INTEGRATION or sys.platform.startswith('linux'), 'Linux quota or Docker integration')
    def test_real_quota_blocks_large_heap_and_mmap_preserves_small_work(self):
        MEMORY_BYTES = 256 * 1024 * 1024
        guard=ROOT/'tests/grader_limits.py'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();worker=root/'worker.py'
            worker.write_text('import errno,mmap,resource\nassert sum(range(10))==45\n'
                f'limit={MEMORY_BYTES}\nassert resource.getrlimit(resource.RLIMIT_AS)==(limit,limit)\n'
                'with mmap.mmap(-1,1024*1024) as small:small[0]=1\n'
                'for allocate in (lambda:mmap.mmap(-1,limit+1024*1024),lambda:bytearray(limit+1024*1024),\n'
                ' lambda:[str(i).zfill(16384) for i in range(limit//16384+1)]):\n'
                ' try:value=allocate()\n except MemoryError:continue\n'
                ' except OSError as exc:\n  if exc.errno==errno.ENOMEM:continue\n  raise\n'
                ' raise AssertionError("memory_quota_bypassed")\n'
                'try:resource.setrlimit(resource.RLIMIT_AS,(limit*2,limit*2))\n'
                'except (OSError,ValueError):pass\nelse:raise AssertionError("hard_limit_raised")\n'
                'print("bounded_worker_pass")\n')
            if INTEGRATION:
                result=run_sandbox(root,str(worker),timeout=15)
                result.stdout=result.stdout.decode();result.stderr=result.stderr.decode()
            else:
                result=subprocess.run([sys.executable,'-I','-S','-B',str(guard),str(worker)],
                    env={'PATH':'/usr/bin:/bin'},capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout.strip(),'bounded_worker_pass')

    @unittest.skipUnless(INTEGRATION,'Docker candidate loading')
    def test_candidate_cannot_allocate_past_quota_in_default_argument(self):
        MEMORY_BYTES = 256 * 1024 * 1024
        from tests.coding_trials import grade_source
        source=f"def confidence(response, data='x'*{MEMORY_BYTES+1}):\n return 0\n"
        self.assertFalse(grade_source('confidence-repair',source)['execution'])


if __name__=='__main__':
    unittest.main()
