import importlib.util
import io
import re
import html
from urllib.parse import unquote
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('repository', Path(__file__).resolve().parents[1] / 'tools/repository.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)

class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        shutil.copytree(r.ROOT / 'docs', self.root / 'docs')
        shutil.copy(r.ROOT / 'catalog.json', self.root / 'catalog.json')

    def package(self, version='1.0.0', extra=None):
        path = self.root / 'input.zip'
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('plugin.test/addon.xml', f'<addon id="plugin.test" name="Test" version="{version}"><extension point="xbmc.python.script" library="main.py"/></addon>')
            z.writestr('plugin.test/main.py', 'pass')
            if extra:
                z.writestr(*extra)
        return path

    def test_multi_addon_update_preserves_history(self):
        r.import_zip(self.root, self.package(), 'https://example.org/source')
        r.import_zip(self.root, self.package('1.1.0'), 'https://example.org/source')
        r.build(self.root, check=True)
        self.assertEqual(r.load(self.root)['plugin.test']['version'], '1.1.0')
        self.assertTrue((self.root / 'docs/plugin.test/plugin.test-1.0.0.zip').exists())
        self.assertIn('service.nord.vpn', r.load(self.root))

    def test_mutation_rejected(self):
        r.import_zip(self.root, self.package(), 'https://example.org/source')
        with self.assertRaisesRegex(ValueError, 'immutable'):
            r.import_zip(self.root, self.package(extra=('plugin.test/new.txt', 'changed')), 'https://example.org/source')

    def test_downgrade_rejected(self):
        r.import_zip(self.root, self.package('2.0.0'), 'https://example.org/source')
        with self.assertRaisesRegex(ValueError, 'downgrade'):
            r.import_zip(self.root, self.package(), 'https://example.org/source')

    def test_path_traversal_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            r.inspect(self.package(extra=('plugin.test/../../outside', 'bad')).read_bytes())

    def test_installer_visible_to_kodi_http_directory(self):
        # Kodi HTTPDirectory.cpp requires the decoded href and visible name to
        # match. Its anchor pattern also requires content after the closing tag.
        # https://github.com/xbmc/xbmc/blob/Omega/xbmc/filesystem/HTTPDirectory.cpp
        r.build(self.root)
        page = (self.root / 'docs/index.html').read_text()
        anchors = re.findall(r'<a href="([^"]*)"[^>]*>\s*(.*?)\s*</a>(.+?)(?=<a|</tr|$)', page, re.I)
        visible = [href for href, label, _ in anchors
                   if html.unescape(label.strip()).rstrip('/') == unquote(href).rstrip('/')]
        version = r.load(self.root)[r.REPO_ID]['version']
        installer = f'{r.REPO_ID}-{version}.zip'
        self.assertIn(installer, visible)
        self.assertEqual((self.root / 'docs' / installer).read_bytes(),
                         (self.root / 'docs' / r.REPO_ID / installer).read_bytes())

    def test_stale_index_detected(self):
        (self.root / 'docs/addons.xml').write_text('stale')
        with self.assertRaisesRegex(ValueError, 'stale'):
            r.build(self.root, check=True)

    def test_checksum_detects_tampering(self):
        version = r.load(self.root)['service.nord.vpn']['version']
        p = self.root / f'docs/service.nord.vpn/service.nord.vpn-{version}.zip'
        with zipfile.ZipFile(p, 'a') as z:
            z.writestr('service.nord.vpn/unexpected.txt', 'changed')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            r.build(self.root, check=True)

if __name__ == '__main__':
    unittest.main()
