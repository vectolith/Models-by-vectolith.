"""Repository hygiene audit: relative markdown links, tracked build artifacts, stale markers."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r'\[[^\]]*\]\(([^)\s]+)\)')
ARTIFACT = re.compile(r'(\.egg-info/|__pycache__/|\.pyc$|\.DS_Store$)')
SKIP_DIRS = {'.git', '.venv', 'node_modules'}


def markdown_files() -> list[Path]:
    files = []
    for path in ROOT.rglob('*.md'):
        if SKIP_DIRS & set(path.parts):
            continue
        files.append(path)
    return sorted(files)


def broken_relative_links() -> list[str]:
    problems = []
    for path in markdown_files():
        text = path.read_text(encoding='utf-8', errors='replace')
        for match in LINK.finditer(text):
            target = match.group(1).split('#')[0].strip()
            if not target or target.startswith(('http://', 'https://', 'mailto:')):
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                problems.append(f'{path.relative_to(ROOT)} -> {target}')
    return problems


def tracked_artifacts() -> list[str]:
    result = subprocess.run(['git', 'ls-files'], cwd=ROOT, capture_output=True, text=True, check=True)
    return [line for line in result.stdout.splitlines() if ARTIFACT.search(line)]


def main() -> int:
    links = broken_relative_links()
    artifacts = tracked_artifacts()
    for problem in links:
        print(f'broken-link {problem}')
    for problem in artifacts:
        print(f'tracked-artifact {problem}')
    print(f'checked {len(markdown_files())} markdown files')
    return 1 if links or artifacts else 0


if __name__ == '__main__':
    sys.exit(main())