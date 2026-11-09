#!/usr/bin/env python3
"""Validate generated site structure and local references, without dependencies."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


@dataclass
class Reference:
    url: str
    line: int
    attribute: str


class Page(HTMLParser):
    def __init__(self, path: Path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.ids: set[str] = set()
        self.references: list[Reference] = []
        self.local_ids: list[Reference] = []
        self.problems: list[str] = []
        self.h1_count = 0
        self.has_title = False
        self.lang = ''

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        line = self.getpos()[0]
        if tag == 'html':
            self.lang = data.get('lang') or ''
        if tag == 'h1':
            self.h1_count += 1
        if tag == 'title':
            self.has_title = True
        identity = data.get('id')
        if identity:
            if identity in self.ids:
                self.problems.append(f'line {line}: duplicate id {identity!r}')
            self.ids.add(identity)
        if tag == 'img' and 'alt' not in data:
            self.problems.append(f'line {line}: image is missing an alt attribute')
        for attribute in ('href', 'src', 'poster', 'data-full'):
            if attribute in data:
                value = data[attribute] or ''
                if not value.strip():
                    self.problems.append(f'line {line}: empty {attribute} on <{tag}>')
                else:
                    self.references.append(Reference(value, line, attribute))
        if data.get('srcset'):
            for value in parse_srcset(data['srcset']):
                self.references.append(Reference(value, line, 'srcset'))
        for attribute in ('aria-labelledby', 'aria-describedby', 'aria-controls'):
            for identity in (data.get(attribute) or '').split():
                self.local_ids.append(Reference(identity, line, attribute))
        if data.get('data-filter-group'):
            self.local_ids.append(Reference(data['data-filter-group'], line, 'data-filter-group'))


def parse_srcset(value: str):
    """Read URL candidates, retaining comma-containing data URLs as one token."""
    remaining = value.strip()
    while remaining:
        remaining = remaining.lstrip(' ,\t\r\n')
        if not remaining:
            break
        match = re.match(r'\S+', remaining)
        token = match.group(0)
        remaining = remaining[len(token):]
        # A URL token may directly end a candidate, before any descriptor.
        if token.endswith(','):
            yield token.rstrip(',')
            continue
        if not token.startswith('data:') and ',' in token:
            first, rest = token.split(',', 1)
            yield first
            remaining = rest + remaining
            continue
        yield token
        if remaining.lstrip().startswith(','):
            remaining = remaining.lstrip()[1:]
        elif ',' in remaining:
            remaining = remaining.split(',', 1)[1]
        else:
            remaining = ''


def resolve_reference(root: Path, source: Path, value: str, base_path: str):
    parts = urlsplit(value)
    if parts.scheme or parts.netloc:
        return None
    path = unquote(parts.path)
    if not path:
        target = source
    elif path.startswith('/'):
        if base_path and (path == base_path or path.startswith(base_path + '/')):
            path = path[len(base_path):]
        target = root / path.lstrip('/')
    else:
        target = source.parent / path
    target = target.resolve()
    if not target.is_relative_to(root):
        raise ValueError('reference escapes the published site directory')
    if target.is_dir():
        target = target / 'index.html'
    return target, unquote(parts.fragment)


def validate(root: Path, base_path: str = ''):
    root = root.resolve()
    problems = []
    pages = {}
    references = 0
    if not root.is_dir():
        return {'pages': 0, 'local_references': 0, 'errors': [f'Site directory does not exist: {root}']}
    for path in sorted(root.rglob('*.html')):
        page = Page(path)
        page.feed(path.read_text(encoding='utf-8'))
        pages[path] = page
        label = path.relative_to(root)
        problems.extend(f'{label}: {problem}' for problem in page.problems)
        if page.h1_count != 1:
            problems.append(f'{label}: expected one h1, found {page.h1_count}')
        if not page.has_title:
            problems.append(f'{label}: missing document title')
        if not page.lang:
            problems.append(f'{label}: missing document language')
        for ref in page.local_ids:
            if ref.url not in page.ids:
                problems.append(f'{label}:{ref.line}: {ref.attribute} points to missing id {ref.url!r}')
    if not pages:
        problems.append('No HTML pages were found')
    if root / 'index.html' not in pages:
        problems.append('Missing site entry point index.html')

    def check(source, ref):
        nonlocal references
        label = source.relative_to(root)
        try:
            resolved = resolve_reference(root, source, ref.url, base_path)
        except ValueError as exc:
            problems.append(f'{label}:{ref.line}: {ref.attribute} {ref.url!r}: {exc}')
            return
        if resolved is None:
            return
        references += 1
        target, fragment = resolved
        if not target.is_file():
            problems.append(f'{label}:{ref.line}: missing {ref.attribute} target {ref.url!r}')
        elif fragment and target.suffix.lower() == '.html' and target in pages and fragment not in pages[target].ids:
            problems.append(f'{label}:{ref.line}: missing fragment in {ref.url!r}')

    for page in pages.values():
        for ref in page.references:
            check(page.path, ref)
    css_url = re.compile(r'url\(\s*[\'\"]?([^\'\")]+)[\'\"]?\s*\)', re.IGNORECASE)
    for path in sorted(root.rglob('*.css')):
        content = re.sub(r'/\*.*?\*/', '', path.read_text(encoding='utf-8'), flags=re.S)
        for match in css_url.finditer(content):
            ref = Reference(match.group(1).strip(), content.count('\n', 0, match.start()) + 1, 'CSS url')
            check(path, ref)
    return {'pages': len(pages), 'local_references': references, 'errors': problems}


def main():
    project = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', nargs='?', type=Path, default=project / 'docs')
    parser.add_argument('--base-path', default=None, help='GitHub Pages project prefix, e.g. /Weilin_Sean_Wan')
    args = parser.parse_args()
    base_path = args.base_path
    if base_path is None:
        settings = project / 'content/site.json'
        base_path = urlsplit(json.loads(settings.read_text()).get('public_url', '')).path if settings.exists() else ''
    report = validate(args.directory, base_path.rstrip('/'))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report['errors'] else 0


if __name__ == '__main__':
    sys.exit(main())
