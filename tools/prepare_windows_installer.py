"""Prepare verified build tools in a private directory, without global install.

Inno's CURRENTUSER/PORTABLE mode disables registry entries, file associations and
shortcuts. WebView2's prerequisite is downloaded and verified, never installed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.packaging.build_windows_installer import build_environment


def signed(path, publisher):
    with tempfile.TemporaryDirectory(prefix='router-build-signature-') as folder:
        script=Path(folder)/'verify.ps1'
        script.write_text("param([string]$File,[string]$Publisher)\n$s=Get-AuthenticodeSignature -LiteralPath $File; if($s.Status -ne 'Valid' -or $s.SignerCertificate.GetNameInfo([System.Security.Cryptography.X509Certificates.X509NameType]::SimpleName,$false) -ne $Publisher){exit 1}")
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(script),str(path),publisher],env=build_environment(),check=True,capture_output=True,timeout=60)


def download(url, destination, digest=None):
    with urllib.request.urlopen(url,timeout=60) as response:
        data=response.read(16*1024*1024+1)
    if len(data)>16*1024*1024 or digest and hashlib.sha256(data).hexdigest()!=digest:
        raise ValueError('Build tool size/checksum verification failed.')
    destination.write_bytes(data)


def prepare(destination):
    if sys.platform!='win32':raise ValueError('Native Windows tools only.')
    destination=Path(destination).resolve();destination.mkdir(parents=True,exist_ok=True)
    lock=json.loads((ROOT/'tools/inno-setup.lock.json').read_text())
    compiler=destination/('inno-'+lock['version'])
    if not all((compiler/name).is_file() and hashlib.sha256((compiler/name).read_bytes()).hexdigest()==digest for name,digest in lock['files'].items()):
        setup=destination/('innosetup-'+lock['version']+'.exe');download(lock['source'],setup,lock['sha256']);signed(setup,lock['publisher'])
        subprocess.run([str(setup),'/CURRENTUSER','/PORTABLE=1','/VERYSILENT','/NORESTART','/DIR='+str(compiler)],check=True,timeout=120)
        if not all((compiler/name).is_file() and hashlib.sha256((compiler/name).read_bytes()).hexdigest()==digest for name,digest in lock['files'].items()):
            raise ValueError('Compiler verification failed after portable extraction.')
    bootstrapper=destination/'MicrosoftEdgeWebview2Setup.exe'
    if not bootstrapper.is_file():download('https://go.microsoft.com/fwlink/p/?LinkId=2124703',bootstrapper)
    signed(bootstrapper,'Microsoft Corporation')
    report={'compiler':str(compiler/'ISCC.exe'),'compilerVersion':lock['version'],'webview2Bootstrapper':str(bootstrapper),
            'bootstrapperSha256':hashlib.sha256(bootstrapper.read_bytes()).hexdigest(),'prerequisiteInstalled':False}
    (destination/'tools-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'state/installer-build-tools')
    args=parser.parse_args();print(json.dumps(prepare(args.output)))
