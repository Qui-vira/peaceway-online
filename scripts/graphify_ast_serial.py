"""Serial AST extraction — graphify's parallel pool silently drops files here.

See CLAUDE.md ("Known issue: run AST extraction serially on this machine").
Run from the repo root:  python scripts/graphify_ast_serial.py
"""
import json
from pathlib import Path
from graphify.detect import detect
from graphify.extract import collect_files, extract

d = detect(Path('.'))
for cat in ('image', 'video'):          # website assets / slide exports, not architecture
    d['files'][cat] = []
d['total_files'] = sum(len(v) for v in d['files'].values())
Path('graphify-out').mkdir(exist_ok=True)
Path('graphify-out/.graphify_detect.json').write_text(
    json.dumps(d, ensure_ascii=False), encoding='utf-8')

files = [p for f in d['files']['code']
         for p in (collect_files(Path(f)) if Path(f).is_dir() else [Path(f)])]
r = extract(files, cache_root=Path('.'), parallel=False)     # <-- the fix
Path('graphify-out/.graphify_ast.json').write_text(
    json.dumps(r, indent=2, ensure_ascii=False), encoding='utf-8')
print('{} nodes, {} edges from {} files'.format(
    len(r['nodes']), len(r['edges']), len(files)))
