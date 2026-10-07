"""Compile the native launcher against a disposable registry key, never Environment."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import queue
import threading
import tempfile
import unittest
import uuid


@unittest.skipUnless(os.name == 'nt', 'Windows native compiler and registry')
class NativeDisconnectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import winreg
        cls.winreg = winreg
        compiler = Path(os.environ['WINDIR']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
        if not compiler.is_file():
            raise unittest.SkipTest('Native .NET Framework compiler unavailable')
        cls.temporary = tempfile.TemporaryDirectory(prefix='router-native-disconnect-')
        cls.root = Path(cls.temporary.name)
        cls.registry_parent = 'Software\\CodexRouterQA\\' + uuid.uuid4().hex
        cls.registry_key = cls.registry_parent + '\\Environment'
        source = Path(__file__).resolve().parents[1]
        launcher = (source / 'InstalledLauncher.cs').read_text(encoding='utf-8')
        needle = 'Registry.CurrentUser.CreateSubKey("Environment")'
        if launcher.count(needle) != 1:
            raise RuntimeError('Native fixture registry redirection must remain explicit')
        launcher = launcher.replace(needle, 'Registry.CurrentUser.CreateSubKey(' + json.dumps(cls.registry_key) + ')')
        (cls.root / 'InstalledLauncher.cs').write_text(launcher, encoding='utf-8')
        shutil.copy2(source / 'WindowsLayout.cs', cls.root / 'WindowsLayout.cs')
        binary = cls.root / 'application/bin/codex-router.exe'
        binary.parent.mkdir(parents=True)
        cls.binary = binary
        subprocess.run([str(compiler), '/nologo', '/target:exe', '/r:System.Core.dll',
                        '/r:System.Web.Extensions.dll', '/r:System.Windows.Forms.dll',
                        '/out:' + str(binary), str(cls.root / 'InstalledLauncher.cs'),
                        str(cls.root / 'WindowsLayout.cs')], check=True, capture_output=True,
                       timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
        version='0.0.0-aaaaaaaaaaaaaaaa'
        resources=binary.parent.parent/'versions'/version/'Resources';resources.mkdir(parents=True)
        runtime=resources.parent/'runtime/echo.exe';runtime.parent.mkdir()
        monitor=resources.parent/'bin/monitor.exe';monitor.parent.mkdir();monitor.touch()
        (resources/'application.json').write_text(json.dumps({'schema':1,'layout':'windows-install-v1',
            'runtime':'runtime/echo.exe','monitor':'bin/monitor.exe'}))
        (binary.parent.parent/'active.json').write_text(json.dumps({'schema':1,'versionDirectory':version}))
        echo=cls.root/'Echo.cs'
        echo.write_text('using System; class Echo { static void Main() { string line; while ((line=Console.ReadLine())!=null) { Console.Out.WriteLine(line); Console.Out.Flush(); Console.Error.WriteLine("err:"+line); Console.Error.Flush(); } } }')
        subprocess.run([str(compiler),'/nologo','/target:exe','/out:'+str(runtime),str(echo)],
                       check=True,capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)

    @classmethod
    def tearDownClass(cls):
        try:
            for key in (cls.registry_key, cls.registry_parent):
                try:
                    cls.winreg.DeleteKey(cls.winreg.HKEY_CURRENT_USER, key)
                except FileNotFoundError:
                    pass
        finally:
            cls.temporary.cleanup()

    def fixture(self, wrapper, current, previous):
        data = self.root / ('data-' + uuid.uuid4().hex)
        (data / 'state').mkdir(parents=True)
        receipt = data / 'state/desktop-integration.json'
        receipt.write_text(json.dumps({'schema': 1, 'platform': 'win32', 'status': 'registered',
                                      'wrapper': wrapper, 'previous': previous}), encoding='utf-8')
        with self.winreg.CreateKey(self.winreg.HKEY_CURRENT_USER, self.registry_key) as key:
            self.winreg.SetValueEx(key, 'CODEX_CLI_PATH', 0, self.winreg.REG_SZ, current)
        return data, receipt

    def disconnect(self, data):
        return subprocess.run([str(self.binary), '--data-root', str(data), '--remove-integration-json'],
                              capture_output=True, timeout=15,
                              creationflags=subprocess.CREATE_NO_WINDOW).returncode

    def read_environment(self):
        with self.winreg.OpenKey(self.winreg.HKEY_CURRENT_USER, self.registry_key) as key:
            return self.winreg.QueryValueEx(key, 'CODEX_CLI_PATH')

    def test_owned_windows_path_restores_literal_expand_string(self):
        wrapper = str(self.binary.resolve())
        before = r'%SystemRoot%\synthetic-before.exe'
        data, receipt = self.fixture(wrapper, wrapper, {'value': before, 'kind': 2})
        self.assertEqual(self.disconnect(data), 0)
        self.assertEqual(self.read_environment(), (before, self.winreg.REG_EXPAND_SZ))
        self.assertFalse(receipt.exists())

    def test_owned_forward_slash_alias_is_equivalent(self):
        wrapper = str(self.binary.resolve()).replace('\\', '/')
        data, receipt = self.fixture(wrapper, wrapper, {'value': 'synthetic-before.exe', 'kind': 1})
        self.assertEqual(self.disconnect(data), 0)
        self.assertEqual(self.read_environment(), ('synthetic-before.exe', self.winreg.REG_SZ))
        self.assertFalse(receipt.exists())

    def test_foreign_current_connection_remains_untouched(self):
        wrapper = str(self.binary.resolve())
        data, receipt = self.fixture(wrapper, 'synthetic-foreign.exe', {'value': None, 'kind': 1})
        self.assertEqual(self.disconnect(data), 2)
        self.assertEqual(self.read_environment(), ('synthetic-foreign.exe', self.winreg.REG_SZ))
        self.assertTrue(receipt.exists())

    def test_foreign_receipt_wrapper_remains_untouched(self):
        data, receipt = self.fixture(str(self.root / 'foreign.exe'), 'synthetic-current.exe',
                                     {'value': None, 'kind': 1})
        self.assertEqual(self.disconnect(data), 2)
        self.assertEqual(self.read_environment(), ('synthetic-current.exe', self.winreg.REG_SZ))
        self.assertTrue(receipt.exists())

    def test_absent_previous_value_is_removed(self):
        wrapper = str(self.binary.resolve())
        data, receipt = self.fixture(wrapper, wrapper, {'value': None, 'kind': 1})
        self.assertEqual(self.disconnect(data), 0)
        with self.assertRaises(FileNotFoundError):
            self.read_environment()
        self.assertFalse(receipt.exists())

    def test_small_stdio_messages_arrive_before_input_is_closed(self):
        process=subprocess.Popen([str(self.binary),'app-server'],stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
        output=queue.Queue();errors=queue.Queue()
        def read(stream,target):
            for line in stream:target.put(line)
        readers=[threading.Thread(target=read,args=(process.stdout,output),daemon=True),
                 threading.Thread(target=read,args=(process.stderr,errors),daemon=True)]
        for reader in readers:reader.start()
        try:
            for message in (b'{"id":1}\n',b'{"id":2}\n'):
                process.stdin.write(message);process.stdin.flush()
                self.assertEqual(output.get(timeout=3).rstrip(b'\r\n'),message.rstrip(b'\n'))
                self.assertEqual(errors.get(timeout=3).rstrip(b'\r\n'),b'err:'+message.rstrip(b'\n'))
                self.assertIsNone(process.poll())
        finally:
            process.stdin.close()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
            for reader in readers:reader.join(timeout=2)
            process.stdout.close();process.stderr.close()
        self.assertEqual(process.returncode,0)


if __name__ == '__main__':
    unittest.main()
