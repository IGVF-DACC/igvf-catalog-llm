"""Merge curated edge subtypes into LangChain ArangoGraph schema."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_curated_edge_schema(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


def _property_type(prop: Dict[str, Any]) -> str:
    type_value = prop.get('type')
    if isinstance(type_value, list):
        non_null = [item for item in type_value if item != 'null']
        return str(non_null[0]) if non_null else 'str'
    if type_value is None:
        return 'str'
    return str(type_value)


def _compact_property(prop: Dict[str, Any]) -> Dict[str, Any]:
    """Keep name/type/enum for AQL; drop examples and descriptions."""
    compact: Dict[str, Any] = {
        'name': prop['name'],
        'type': _property_type(prop),
    }
    if 'enum' in prop:
        compact['enum'] = prop['enum']
    return compact


_DISCRIMINATOR_KEYS = ('method', 'source', 'label')
_COLLECTION_DISCRIMINATOR_KEYS = {
    'genes_genes': ('source',),
}
# Shared handles only; full field lists live on subtypes.
_SHARED_EDGE_PROPERTY_NAMES = ('_from', '_to')


def _discriminator_keys_for(collection_name: str) -> tuple:
    return _COLLECTION_DISCRIMINATOR_KEYS.get(
        collection_name, _DISCRIMINATOR_KEYS
    )


def _compact_discriminators(
    discriminators: Optional[Dict[str, Any]],
    collection_name: str,
) -> Dict[str, Any]:
    if not discriminators:
        return {}
    allowed = _discriminator_keys_for(collection_name)
    return {
        key: discriminators[key]
        for key in allowed
        if key in discriminators
    }


def _shared_edge_properties(subtypes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Minimal edge_properties for multi-shape edges (_from/_to only)."""
    by_name: Dict[str, Dict[str, Any]] = {}
    for subtype in subtypes:
        for prop in subtype.get('properties') or []:
            name = prop.get('name')
            if name not in _SHARED_EDGE_PROPERTY_NAMES or name in by_name:
                continue
            by_name[name] = {
                'name': name,
                'type': _property_type(prop),
            }
    # Stable order even if a subtype omits one of the handles.
    return [
        by_name.get(name, {'name': name, 'type': 'str'})
        for name in _SHARED_EDGE_PROPERTY_NAMES
    ]


def _compact_subtype_properties(
    subtype: Dict[str, Any],
    collection_name: str,
) -> List[Dict[str, Any]]:
    """Subtype fields minus discriminator keys (those live under discriminators)."""
    skip = set(_discriminator_keys_for(collection_name))
    # Also skip method/source/label even if this collection only exposes source
    # as a discriminator, so enums are not duplicated under properties.
    skip.update(_DISCRIMINATOR_KEYS)
    compacted: List[Dict[str, Any]] = []
    for prop in subtype.get('properties') or []:
        name = prop.get('name')
        if not name or name in skip:
            continue
        compacted.append(_compact_property(prop))
    return compacted


def _compact_subtype(
    subtype: Dict[str, Any],
    collection_name: str,
) -> Dict[str, Any]:
    # Omit schema_file: useful for curated debugging, not for the LLM prompt.
    return {
        'discriminators': _compact_discriminators(
            subtype.get('discriminators'), collection_name
        ),
        'properties': _compact_subtype_properties(subtype, collection_name),
    }


def build_curated_edge_collection_entry(
    collection_name: str,
    curated_collection: Dict[str, Any],
) -> Dict[str, Any]:
    raw_subtypes = curated_collection.get('subtypes') or []
    subtypes = [
        _compact_subtype(subtype, collection_name)
        for subtype in raw_subtypes
    ]
    return {
        'collection_name': collection_name,
        'collection_type': 'edge',
        'edge_properties': _shared_edge_properties(raw_subtypes),
        'subtypes': subtypes,
    }


def merge_curated_edge_schema(
    graph_schema: Dict[str, Any],
    curated_edge_schema: Dict[str, Any],
) -> Dict[str, Any]:
    """Return a deep-copied schema with matching edge collections enriched.

    Node (document) collections are left unchanged. Edge collections present
    in curated_edge_schema are replaced with subtype-aware entries. Edges
    missing from curated data keep their live-sampled schema entry.
    """
    merged = copy.deepcopy(graph_schema)
    curated_collections = curated_edge_schema.get('collections') or {}
    collection_schema = merged.get('Collection Schema') or []

    updated: List[Dict[str, Any]] = []
    for entry in collection_schema:
        name = entry.get('collection_name')
        if (
            entry.get('collection_type') == 'edge'
            and name in curated_collections
        ):
            updated.append(
                build_curated_edge_collection_entry(
                    name, curated_collections[name]
                )
            )
        else:
            updated.append(entry)

    merged['Collection Schema'] = updated
    return merged


def apply_curated_edge_schema(
    graph: Any,
    curated_path: Path,
) -> Dict[str, Any]:
    """Merge curated edges into graph.schema. Returns the merged schema."""
    curated = load_curated_edge_schema(curated_path)
    merged_schema = merge_curated_edge_schema(graph.schema, curated)
    graph.set_schema(merged_schema)
    return merged_schema
