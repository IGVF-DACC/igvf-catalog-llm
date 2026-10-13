#!/usr/bin/env python3
"""Generate a compact curated edge schema from igvf-catalog JSON Schemas.

Reads adapter/source-specific files under data/schemas/edges/ and groups them
by db_collection_name. Each file becomes one subtype with method/source/label
discriminators and a trimmed property list. Collections with fewer than two
subtypes are omitted (live schema is enough).

This does not query ArangoDB. Commit both outputs in the repo; the Flask app
picks one via CURATED_EDGE_SCHEMA_PATH (same pattern as BACKEND_URL):
  - curated_edge_schema.dev.json  ← igvf-catalog ``dev`` (demo / dev / local)
  - curated_edge_schema.prod.json ← igvf-catalog ``main`` (production)

Default GitHub ref is ``dev``, or ``IGVF_CATALOG_SCHEMA_REF`` if set.

Examples:
  # Local checkout of igvf-catalog
  python scripts/generate_curated_edge_schema.py \\
    --schemas-dir /path/to/igvf-catalog/data/schemas/edges \\
    --output curated_edge_schema.dev.json

  # Regenerate both committed files
  python scripts/generate_curated_edge_schema.py --from-github --ref dev \\
    --output curated_edge_schema.dev.json
  python scripts/generate_curated_edge_schema.py --from-github --ref main \\
    --output curated_edge_schema.prod.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

DEFAULT_GITHUB_REPO = 'IGVF-DACC/igvf-catalog'
DEFAULT_GITHUB_EDGES_PATH = 'data/schemas/edges'


def default_github_ref() -> str:
    """Catalog branch for --from-github: env override, else ``dev``."""
    return os.environ.get('IGVF_CATALOG_SCHEMA_REF', 'dev')


SKIP_FILES = frozenset({'edges.base.json'})
# Natural-language and ingest discriminators for multi-shape edge collections.
DISCRIMINATOR_FIELDS = ('method', 'source', 'label')
# Per-collection overrides (e.g. genes_genes shapes differ by source only).
COLLECTION_DISCRIMINATOR_FIELDS = {
    'genes_genes': ('source',),
}
# Keep these on the live LIMIT-1 schema; do not curate subtypes.
EXCLUDED_COLLECTIONS = frozenset({
    'ontology_terms_ontology_terms',
})
MAX_DESCRIPTION_LEN = 160
MIN_SUBTYPES_PER_COLLECTION = 2


def _http_get_json(url: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={'Accept': 'application/vnd.github+json',
                 'User-Agent': 'igvf-catalog-llm'},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def _http_get_bytes(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={'User-Agent': 'igvf-catalog-llm'},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def download_edge_schemas(
    repo: str = DEFAULT_GITHUB_REPO,
    ref: Optional[str] = None,
    edges_path: str = DEFAULT_GITHUB_EDGES_PATH,
    dest_dir: Optional[Path] = None,
) -> Path:
    """Download edge schema JSON files from GitHub into dest_dir."""
    if ref is None:
        ref = default_github_ref()
    if dest_dir is None:
        dest_dir = Path(tempfile.mkdtemp(prefix='igvf-edge-schemas-'))
    dest_dir.mkdir(parents=True, exist_ok=True)

    api_url = (
        f'https://api.github.com/repos/{repo}/contents/{edges_path}?ref={ref}'
    )
    listing = _http_get_json(api_url)
    if not isinstance(listing, list):
        raise RuntimeError(f'Unexpected GitHub API response for {api_url}')

    downloaded = 0
    for entry in listing:
        name = entry.get('name', '')
        if entry.get('type') != 'file' or not name.endswith('.json'):
            continue
        download_url = entry.get('download_url')
        if not download_url:
            continue
        (dest_dir / name).write_bytes(_http_get_bytes(download_url))
        downloaded += 1

    if downloaded == 0:
        raise RuntimeError(f'No JSON schema files downloaded from {api_url}')
    return dest_dir


def _normalize_type(type_value: Any) -> Optional[Union[str, List[str]]]:
    if type_value is None:
        return None
    if isinstance(type_value, list):
        return [str(item) for item in type_value]
    return str(type_value)


def _truncate(text: Optional[str], max_len: int = MAX_DESCRIPTION_LEN) -> Optional[str]:
    if not text:
        return None
    text = ' '.join(str(text).split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + '…'


def _enum_values(prop_schema: Dict[str, Any]) -> Optional[List[Any]]:
    if 'enum' not in prop_schema:
        return None
    values = prop_schema['enum']
    if not isinstance(values, list):
        return [values]
    return values


def _iter_property_blocks(schema: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    """Yield properties objects from the schema (including allOf branches)."""
    properties = schema.get('properties')
    if isinstance(properties, dict):
        yield properties

    for block in schema.get('allOf') or []:
        if not isinstance(block, dict):
            continue
        # Skip pure $ref blocks (edges.base.json); local overrides live beside them.
        if set(block.keys()) == {'$ref'}:
            continue
        nested = block.get('properties')
        if isinstance(nested, dict):
            yield nested
        for child in _iter_property_blocks(block):
            if child is not nested:
                yield child


def extract_properties(schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for properties in _iter_property_blocks(schema):
        for name, prop_schema in properties.items():
            if not isinstance(prop_schema, dict):
                prop_schema = {}
            entry: Dict[str, Any] = {'name': name}
            type_value = _normalize_type(prop_schema.get('type'))
            if type_value is not None:
                entry['type'] = type_value
            enum_values = _enum_values(prop_schema)
            if enum_values is not None:
                entry['enum'] = enum_values
            if 'example' in prop_schema:
                entry['example'] = prop_schema['example']
            description = _truncate(prop_schema.get('description'))
            if description:
                entry['description'] = description
            # Later local blocks override earlier ones (e.g. base then subtype).
            if name in merged:
                merged[name].update(entry)
            else:
                merged[name] = entry
    return list(merged.values())


def discriminator_fields_for(collection_name: str) -> tuple:
    return COLLECTION_DISCRIMINATOR_FIELDS.get(
        collection_name, DISCRIMINATOR_FIELDS
    )


def extract_discriminators(
    properties: List[Dict[str, Any]],
    fields: Optional[tuple] = None,
) -> Dict[str, List[Any]]:
    if fields is None:
        fields = DISCRIMINATOR_FIELDS
    by_name = {prop['name']: prop for prop in properties}
    discriminators: Dict[str, List[Any]] = {}
    for field in fields:
        prop = by_name.get(field)
        if not prop:
            continue
        if 'enum' in prop:
            discriminators[field] = prop['enum']
        elif 'example' in prop:
            discriminators[field] = [prop['example']]
    return discriminators


def parse_edge_schema_file(path: Path) -> Optional[Dict[str, Any]]:
    if path.name in SKIP_FILES:
        return None
    schema = json.loads(path.read_text())
    collection = schema.get('db_collection_name')
    if not collection:
        # Fallback: filename prefix before first dot, e.g. variants_proteins.ASB.json
        collection = path.name.split('.', 1)[0]
    if collection in EXCLUDED_COLLECTIONS:
        return None
    properties = extract_properties(schema)
    subtype: Dict[str, Any] = {
        'schema_file': path.name,
        'schema_id': schema.get('$id') or path.name,
        'db_collection_name': collection,
        'discriminators': extract_discriminators(
            properties,
            fields=discriminator_fields_for(collection),
        ),
        'properties': properties,
    }
    return subtype


def build_curated_schema(
    schemas_dir: Path,
    source: Optional[str] = None,
) -> Dict[str, Any]:
    schemas_dir = schemas_dir.resolve()
    if not schemas_dir.is_dir():
        raise FileNotFoundError(f'Schemas directory not found: {schemas_dir}')

    collections: Dict[str, Dict[str, Any]] = {}
    files = sorted(schemas_dir.glob('*.json'))
    for path in files:
        subtype = parse_edge_schema_file(path)
        if subtype is None:
            continue
        collection_name = subtype['db_collection_name']
        bucket = collections.setdefault(
            collection_name,
            {
                'collection_name': collection_name,
                'collection_type': 'edge',
                'subtypes': [],
            },
        )
        # Keep subtype payload free of redundant collection name at top level copy
        subtype_payload = {
            key: value
            for key, value in subtype.items()
            if key != 'db_collection_name'
        }
        bucket['subtypes'].append(subtype_payload)

    # Single-subtype collections stay on the live LIMIT-1 schema sample.
    collections = {
        name: bucket
        for name, bucket in collections.items()
        if (
            name not in EXCLUDED_COLLECTIONS
            and len(bucket['subtypes']) >= MIN_SUBTYPES_PER_COLLECTION
        )
    }

    return {
        'source': source or str(schemas_dir),
        'schema_count': sum(len(item['subtypes']) for item in collections.values()),
        'collection_count': len(collections),
        'collections': dict(sorted(collections.items())),
    }


def write_curated_schema(data: Dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2, sort_keys=False) + '\n')


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            'Generate curated edge collection subtypes from igvf-catalog '
            'JSON Schemas (method/source/label enums + properties).'
        )
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        '--schemas-dir',
        type=Path,
        help='Local path to igvf-catalog data/schemas/edges',
    )
    source.add_argument(
        '--from-github',
        action='store_true',
        help='Download edge schemas from GitHub instead of using a local directory',
    )
    parser.add_argument(
        '--repo',
        default=DEFAULT_GITHUB_REPO,
        help=f'GitHub repo for --from-github (default: {DEFAULT_GITHUB_REPO})',
    )
    parser.add_argument(
        '--ref',
        default=None,
        help=(
            'Git ref for --from-github (default: IGVF_CATALOG_SCHEMA_REF or '
            f'{default_github_ref()!r}; use main for production)'
        ),
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('curated_edge_schema.dev.json'),
        help='Output JSON path (default: curated_edge_schema.dev.json)',
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    try:
        if args.from_github:
            ref = args.ref or default_github_ref()
            schemas_dir = download_edge_schemas(repo=args.repo, ref=ref)
            source = f'github:{args.repo}@{ref}:{DEFAULT_GITHUB_EDGES_PATH}'
        else:
            schemas_dir = args.schemas_dir
            source = str(schemas_dir.resolve())

        curated = build_curated_schema(schemas_dir, source=source)
        write_curated_schema(curated, args.output)
    except (OSError, RuntimeError, urllib.error.URLError, json.JSONDecodeError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1

    print(
        f'Wrote {args.output} '
        f'({curated["collection_count"]} collections, '
        f'{curated["schema_count"]} subtypes)'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
