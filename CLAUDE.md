## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, keep the graph current (AST-only, no API cost) — but **do not use a
  plain `graphify update .` on this machine**: it silently drops files. Use
  `python scripts/graphify_ast_serial.py` instead, and read the known-issue section below first.

### Known issue: run AST extraction serially on this machine

graphify's parallel AST worker pool crashes here (Windows + Python 3.14) and **fails
silently** — affected files produce zero nodes and are simply absent from the graph, with
only a `worker failed ... process pool was terminated abruptly` warning in the output.
Measured on 2026-07-26: the parallel path yielded 2417 nodes / 7939 edges, serial yielded
**2890 / 9276** — ~470 nodes and ~1300 edges lost, including `app/bot/dispatcher.py` and
`app/bot/errors.py`.

A plain `graphify update .` uses the parallel path. Until the upstream bug is fixed, extract
with `parallel=False`:

Save as `scripts/graphify_ast_serial.py` and run it from the repo root:

```python
"""Serial AST extraction — graphify's parallel pool silently drops files here."""
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
```

Sanity check after any run: `get_session()` should be the top god node (~206 degree), and
the graph should hold **~3300 nodes**. A materially smaller graph means the pool crashed.

Two more things worth knowing when rebuilding:

- **Exclude `web/public` images and the presentation media.** graphify gives every image its
  own vision pass; the ~350 image/video files here are website assets and slide exports, so
  including them costs hundreds of agent calls for no architectural insight.
- **The shrink guard is load-bearing.** It refuses to overwrite `graph.json` with a smaller
  graph. If it fires, find out *why* before forcing — on 2026-07-26 it correctly caught a
  rebuild that would have dropped 314 document nodes extracted by an earlier, deeper pass.
