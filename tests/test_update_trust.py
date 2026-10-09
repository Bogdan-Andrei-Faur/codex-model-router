"""Independent signatures, altered releases, target replay and fail-closed handoff."""
import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
except ImportError:
    Ed25519PrivateKey = None
from codex_model_router.update_trust import DOMAIN, verify, load_keys, TrustError, MANIFEST_NAME
from codex_model_router.updates import UpdateManager, REPOSITORY, installer_name
from tools.packaging.release_manifest import sign


@unittest.skipUnless(Ed25519PrivateKey, 'Install tools/packaging/requirements-update.txt to verify signatures')
class SignedUpdateTests(unittest.TestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.generate()
        public = self.key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.keys = {hashlib.sha256(public).hexdigest(): base64.b64encode(public).decode()}
        self.package = dict(version='1.2.0', name=installer_name('1.2.0','macos','arm64'), size=7, sha256=hashlib.sha256(b'fixture').hexdigest())
        self.payload = dict(schema=1, repository=REPOSITORY, version='1.2.0', created=1000, expires=2000,
                            assets=[dict(platform='macos',arch='arm64',**{k:v for k,v in self.package.items() if k!='version'})])

    def envelope(self, payload=None):
        raw = json.dumps(payload or self.payload).encode()
        return json.dumps(dict(schema=1,keyId=next(iter(self.keys)),payload=base64.b64encode(raw).decode(),
            signature=base64.b64encode(self.key.sign(DOMAIN+raw)).decode())).encode()

    def test_signature_is_bound_to_content_publisher_time_repository_and_target(self):
        raw = self.envelope()
        self.assertEqual(verify(raw,self.keys,self.package,'macos','arm64',now=1500)['expires'],2000)
        for blob, keys, package, platform, arch, now in (
            (raw,{},self.package,'macos','arm64',1500),
            (raw,{'a'*64:next(iter(self.keys.values()))},self.package,'macos','arm64',1500),
            (raw,self.keys,dict(self.package,sha256='0'*64),'macos','arm64',1500),
            (raw,self.keys,self.package,'windows','arm64',1500),
            (raw,self.keys,self.package,'macos','x64',1500),
            (raw,self.keys,self.package,'macos','arm64',2000),
            (raw,self.keys,self.package,'macos','arm64',100),
            (self.envelope(dict(self.payload,repository='foreign/repo')),self.keys,self.package,'macos','arm64',1500),
            (raw.replace(b'"schema": 1',b'"schema": 1, "schema": 1'),self.keys,self.package,'macos','arm64',1500),
        ):
            with self.subTest(platform=platform,now=now),self.assertRaises(TrustError): verify(blob,keys,package,platform,arch,now)
        value=json.loads(raw);value['signature']=base64.b64encode(b'0'*64).decode()
        with self.assertRaises(TrustError):verify(json.dumps(value).encode(),self.keys,self.package,'macos','arm64',1500)

    def test_duplicate_target_wrong_size_and_lifetime_are_rejected_even_when_signed(self):
        for field,value in [('assets',self.payload['assets']*2),('expires',1000+181*86400),('schema',False),('schema',True)]:
            with self.subTest(field=field),self.assertRaises(TrustError):
                verify(self.envelope(dict(self.payload,**{field:value})),self.keys,self.package,'macos','arm64',1500)

    def test_signer_roundtrip_and_no_overwrite_keygen(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/self.package['name'];p.write_bytes(b'fixture')
            raw=sign(self.key,'1.2.0',[('macos/arm64',p)],now=1500,validity=1000)
            self.assertEqual(verify(raw,self.keys,self.package,'macos','arm64',1500)['expires'],2500)
            from tools.packaging.release_manifest import generate
            private=Path(folder)/'key.pem';generate(private,'temporary test passphrase')
            before=private.read_bytes()
            self.assertIn(b'ENCRYPTED PRIVATE KEY',before)
            with self.assertRaises(FileExistsError):generate(private,'temporary test passphrase')
            self.assertEqual(before,private.read_bytes())

    def test_manager_authenticates_before_download_and_handoff_reverifies(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'assets').mkdir()
            (root/'assets/update-trust.json').write_text(json.dumps(dict(schema=1,keys=self.keys)))
            payload=dict(self.payload,created=int(time.time())-1,expires=int(time.time())+1000)
            raw=self.envelope(payload)
            base='https://github.com/'+REPOSITORY+'/releases/download/v1.2.0/'
            release=dict(tag_name='v1.2.0',draft=False,prerelease=False,assets=[
                dict(name=self.package['name'],size=7,digest='sha256:'+self.package['sha256'],state='uploaded',browser_download_url=base+self.package['name']),
                dict(name=MANIFEST_NAME,size=len(raw),state='uploaded',browser_download_url=base+MANIFEST_NAME)])
            class Response(io.BytesIO):headers={}
            class Applier:
                def prepare(inner,path,package,envelope,stop):
                    inner.called=True;self.assertEqual(path.read_bytes(),b'fixture');return True
            applier=Applier();applier.called=False
            manager=UpdateManager(root,'1.0.0','macos','arm64',fetcher=lambda:release,
                opener=lambda url:Response(raw if url.endswith(MANIFEST_NAME) else b'fixture'),applier=applier)
            try:
                manager.start('check');manager.future.result(3)
                self.assertTrue(manager.snapshot()['publisherVerified']);self.assertTrue(manager.snapshot()['canUpdate'])
                manager.start('install');manager.future.result(3)
                self.assertTrue(applier.called);self.assertTrue(manager.snapshot()['shutdownForUpdate'])
                self.assertEqual(manager.start('cancel'),'La instalación ya está preparada; espera a que termine.')
                self.assertEqual(manager.start('check'),'La instalación ya está preparada; espera a que termine.')
                self.assertTrue(manager.snapshot()['shutdownForUpdate'])
                self.assertEqual(manager.snapshot()['status'],'installing')
            finally:manager.close()
            # An unsigned latest release never falls back to hash-only installation.
            release['assets'].pop()
            manager=UpdateManager(root,'1.0.0','macos','arm64',fetcher=lambda:release)
            try:
                manager.start('check');manager.future.result(3)
                self.assertEqual(manager.snapshot()['error'],'missing_signature')
                self.assertFalse(manager.snapshot()['canUpdate'])
            finally:manager.close()

    def test_unknown_or_symlinked_trust_store_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'assets').mkdir();path=root/'assets/update-trust.json'
            self.assertEqual(load_keys(root),{})
            path.write_text(json.dumps(dict(schema=1,keys={'bad':next(iter(self.keys.values()))})))
            with self.assertRaises(TrustError):load_keys(root)
