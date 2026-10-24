#!/usr/bin/env python3
"""Import immutable Kodi release ZIPs and generate a multi-add-on repository."""
import argparse
import hashlib
import html
import json
import re
import zipfile
from pathlib import Path, PurePosixPath
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://raw.githubusercontent.com/stefan-commits/kodi-repository/main/docs/'
REPO_ID = 'repository.stefan-commits'


def inspect(data):
    import io
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate ZIP entries')
        for info in z.infolist():
            p = PurePosixPath(info.filename)
            if p.is_absolute() or '..' in p.parts or '\\' in info.filename or (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Unsafe ZIP entry: ' + info.filename)
        manifests = [n for n in names if n.count('/') == 1 and n.endswith('/addon.xml')]
        if len(manifests) != 1:
            raise ValueError('ZIP must contain exactly one addon.id/addon.xml')
        node = ET.fromstring(z.read(manifests[0]))
        aid, version = node.attrib['id'], node.attrib['version']
        if node.tag != 'addon' or not re.fullmatch(r'[a-z0-9]+(?:[._-][a-z0-9]+)*', aid):
            raise ValueError('Invalid add-on ID')
        if not re.fullmatch(r'\d+\.\d+\.\d+', version):
            raise ValueError('Use a stable three-part version, e.g. 1.2.3')
        if manifests[0] != aid + '/addon.xml' or any(not n.startswith(aid + '/') for n in names):
            raise ValueError('All ZIP files must be inside the add-on ID directory')
        for ext in node.findall('extension'):
            if ext.get('library') and aid + '/' + ext.get('library') not in names:
                raise ValueError('Missing extension library')
        assets = {}
        for asset in node.findall('./extension[@point="xbmc.addon.metadata"]/assets/*'):
            if asset.text:
                p = PurePosixPath(asset.text)
                if p.is_absolute() or '..' in p.parts or '\\' in asset.text:
                    raise ValueError('Unsafe asset path')
                assets[asset.text] = z.read(aid + '/' + asset.text)
        if z.testzip():
            raise ValueError('Corrupt ZIP')
        return node, assets


def load(root):
    path = root / 'catalog.json'
    return json.loads(path.read_text()) if path.exists() else {}


def import_zip(root, path, source):
    data = path.read_bytes()
    node, _ = inspect(data)
    aid, version = node.attrib['id'], node.attrib['version']
    catalog = load(root)
    target = root / 'docs' / aid / f'{aid}-{version}.zip'
    if target.exists() and target.read_bytes() != data:
        raise ValueError('Published versions are immutable; bump addon.xml version')
    if aid in catalog and tuple(map(int, version.split('.'))) < tuple(map(int, catalog[aid]['version'].split('.'))):
        raise ValueError('Refusing to downgrade the current version')
    if not source.startswith('https://'):
        raise ValueError('An HTTPS source URL is required')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    catalog[aid] = {'version': version, 'source': source, 'sha256': hashlib.sha256(data).hexdigest()}
    (root / 'catalog.json').write_text(json.dumps(catalog, indent=2, sort_keys=True) + '\n')
    build(root)


def build(root, check=False):
    catalog = load(root)
    if not catalog:
        raise ValueError('Empty catalog')
    addons = ET.Element('addons')
    generated = {'.nojekyll': b''}
    rows = []
    for aid, release in sorted(catalog.items()):
        version = release['version']
        rel = f'{aid}/{aid}-{version}.zip'
        data = (root / 'docs' / rel).read_bytes()
        node, assets = inspect(data)
        if (node.get('id'), node.get('version')) != (aid, version):
            raise ValueError('Catalog metadata mismatch')
        if hashlib.sha256(data).hexdigest() != release['sha256']:
            raise ValueError('Release checksum mismatch: ' + aid)
        addons.append(node)
        for name, content in assets.items():
            generated[f'{aid}/{name}'] = content
        rows.append(f'<li><a href="{rel}">{html.escape(node.get("name", aid))} {version}</a> · <a href="{html.escape(release["source"], quote=True)}">Source</a></li>')
    for path in sorted((root / 'docs').glob('*/*.zip')):
        node, _ = inspect(path.read_bytes())
        if path.parent.name != node.get('id') or path.name != f'{node.get("id")}-{node.get("version")}.zip':
            raise ValueError('Archive filename mismatch')
        generated[str(path.relative_to(root / 'docs')) + '.sha256'] = (hashlib.sha256(path.read_bytes()).hexdigest() + '\n').encode()
    ET.indent(addons, space='  ')
    xml = ET.tostring(addons, encoding='utf-8', xml_declaration=True) + b'\n'
    generated['addons.xml'] = xml
    generated['addons.xml.md5'] = hashlib.md5(xml).hexdigest().encode() + b'\n'
    rv = catalog[REPO_ID]['version']
    installer = f'{REPO_ID}/{REPO_ID}-{rv}.zip'
    generated['index.html'] = f'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stefan's Kodi Repository</title>
<style>body{{font:18px/1.6 system-ui;max-width:760px;margin:60px auto;padding:0 24px;background:#101923;color:#e6eef6}}a{{color:#86d6ff}}h1{{line-height:1.2}}li{{margin:12px 0}}</style>
<h1>Stefan's Kodi Repository</h1>
<p>A growing collection of Kodi add-ons.</p>
<p><a href="{installer}">Download the repository ZIP</a></p>
<p>In Kodi, enable Unknown sources under Settings → System → Add-ons. Choose Add-ons → Install from zip file and select the downloaded repository ZIP. Then choose Install from repository → Stefan's Kodi Repository.</p>
<h2>Available add-ons</h2><ul>{''.join(rows)}</ul>
<p>NordVPN CLI requires Kodi 19 or newer on Linux and the installed NordVPN Linux app. It is an unofficial community add-on.</p>
<p>Enable automatic add-on updates in Kodi to receive future published versions.</p>
<p><a href="https://github.com/stefan-commits/kodi-repository">Repository and publishing instructions</a></p></html>'''.encode()
    for name, data in generated.items():
        path = root / 'docs' / name
        if check:
            if not path.exists() or path.read_bytes() != data:
                raise ValueError('Generated file is stale: ' + name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    imp = sub.add_parser('import')
    imp.add_argument('zip', type=Path)
    imp.add_argument('--source', required=True)
    gen = sub.add_parser('build')
    gen.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.command == 'import':
        import_zip(ROOT, args.zip, args.source)
    else:
        build(ROOT, args.check)
