#!/usr/bin/env python3
"""Parity check for data refactors (see docs/PARITY.md). Usage: python3 tools/parity_check.py <base-ref> [head-ref]
Builds both refs in temporary worktrees, in draft and live mode, and compares outputs. Exit 1 on any difference."""
import json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.abspath(__file__)) + '/..'
EXCLUDE = {'tests/results.json'}


def git(*a, cwd=ROOT):
    return subprocess.run(['git'] + list(a), cwd=cwd, check=True, capture_output=True, text=True).stdout


def canon(b):
    return json.dumps(json.loads(b.decode('utf-8')), ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def build(ref, live, tmp):
    d = os.path.join(tmp, ref.replace('/', '_') + ('-live' if live else '-draft'))
    git('worktree', 'add', '--detach', '-f', d, ref)
    env = {k: v for k, v in os.environ.items() if k != 'PA_LIVE'}
    if live:
        env['PA_LIVE'] = '1'
    subprocess.run([sys.executable, 'tools/build.py'], cwd=d, env=env, check=True, capture_output=True)
    return d


def files(d):
    out = set()
    for r, ds, fs in os.walk(d):
        ds[:] = [x for x in ds if x not in ('.git', 'node_modules', '__pycache__')]
        for f in fs:
            out.add(os.path.relpath(os.path.join(r, f), d))
    return out


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else 'main'
    head = sys.argv[2] if len(sys.argv) > 2 else 'HEAD'
    tracked_base = set(git('ls-tree', '-r', '--name-only', base).split()) - EXCLUDE
    tmp = tempfile.mkdtemp()
    fails, report = [], []
    try:
        for live in (False, True):
            mode = 'live' if live else 'draft'
            b, h = build(base, live, tmp), build(head, live, tmp)
            fb, fh = files(b), files(h)
            n_bytes = n_canon = 0
            for f in sorted((fb | tracked_base) - EXCLUDE):
                if f not in fh:
                    fails.append(f'[{mode}] {f}: missing on head'); continue
                if f not in fb:
                    continue
                x, y = open(os.path.join(b, f), 'rb').read(), open(os.path.join(h, f), 'rb').read()
                if x == y:
                    n_bytes += 1; continue
                if f.endswith(('.json', '.geojson')) and canon(x) == canon(y):
                    n_canon += 1; continue
                fails.append(f'[{mode}] {f}: differs')
            extra = sorted(fh - fb)
            report.append(f'[{mode}] compared {len((fb | tracked_base) - EXCLUDE)} files: {n_bytes} byte-identical, '
                          f'{n_canon} canonical-JSON-equal only, {len([x for x in fails if x.startswith("[" + mode)])} different; '
                          f'{len(extra)} head-only files (not part of parity)')
            git('worktree', 'remove', '--force', b); git('worktree', 'remove', '--force', h)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        git('worktree', 'prune')
    print('\n'.join(report + fails))
    print('PARITY ' + ('FAIL' if fails else 'HOLDS') + f' ({base} vs {head})')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
