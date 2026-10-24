"""Build a reproducible installer ZIP after changing repository metadata/version."""
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET
root = Path(__file__).resolve().parents[1]
source = root / 'repository.stefan-commits'
node = ET.parse(source / 'addon.xml').getroot()
output = root / '.work' / f'{node.get("id")}-{node.get("version")}.zip'
output.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
    for path in sorted(source.rglob('*')):
        if path.is_file():
            info = zipfile.ZipInfo(f'{source.name}/{path.relative_to(source).as_posix()}', (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, path.read_bytes())
print(output)
