import json
from pathlib import Path

from schema_merge import (
    apply_curated_edge_schema,
    build_curated_edge_collection_entry,
    merge_curated_edge_schema,
)


FIXTURE_CURATED = {
    'collections': {
        'variants_proteins': {
            'collection_name': 'variants_proteins',
            'collection_type': 'edge',
            'subtypes': [
                {
                    'schema_file': 'variants_proteins.ASB.json',
                    'discriminators': {
                        'method': ['ADASTRA'],
                        'label': ['allele-specific binding'],
                        'source': ['ADASTRA'],
                    },
                    'properties': [
                        {
                            'name': '_from',
                            'example': 'variants/x',
                            'description': 'long text that should be dropped',
                        },
                        {
                            'name': '_to',
                            'example': 'proteins/y',
                        },
                        {
                            'name': 'method',
                            'type': 'string',
                            'enum': ['ADASTRA'],
                        },
                        {
                            'name': 'label',
                            'type': 'string',
                            'enum': ['allele-specific binding'],
                        },
                        {
                            'name': 'source',
                            'type': 'string',
                            'enum': ['ADASTRA'],
                        },
                        {
                            'name': 'motif_fc',
                            'type': ['number', 'null'],
                            'example': -0.27,
                        },
                    ],
                },
                {
                    'schema_file': 'variants_proteins.pQTL.json',
                    'discriminators': {
                        'method': ['pQTL'],
                        'label': ['pQTL'],
                        'source': ['UKB'],
                    },
                    'properties': [
                        {'name': 'method', 'enum': ['pQTL']},
                        {'name': 'beta', 'type': 'number', 'example': 0.1},
                    ],
                },
            ],
        }
    }
}


def test_build_curated_edge_collection_entry_compacts_for_tokens():
    entry = build_curated_edge_collection_entry(
        'variants_proteins',
        FIXTURE_CURATED['collections']['variants_proteins'],
    )
    assert entry['collection_type'] == 'edge'
    assert 'example_edge' not in entry
    assert len(entry['subtypes']) == 2
    assert entry['subtypes'][0]['discriminators'] == {
        'method': ['ADASTRA'],
        'label': ['allele-specific binding'],
        'source': ['ADASTRA'],
    }
    assert 'required' not in entry['subtypes'][0]
    assert 'schema_file' not in entry['subtypes'][0]

    # 2) Multi-shape edges keep only shared handles at top level
    assert entry['edge_properties'] == [
        {'name': '_from', 'type': 'str'},
        {'name': '_to', 'type': 'str'},
    ]

    asb_props = {
        prop['name']: prop for prop in entry['subtypes'][0]['properties']
    }
    # 3) Discriminator fields are not repeated under properties
    assert set(asb_props) == {'_from', '_to', 'motif_fc'}
    assert 'method' not in asb_props
    assert 'label' not in asb_props
    assert 'source' not in asb_props
    # 1) No examples (or descriptions) on subtype properties
    assert 'example' not in asb_props['motif_fc']
    assert 'description' not in asb_props['motif_fc']
    assert asb_props['motif_fc']['type'] == 'number'
    assert 'example' not in asb_props['_from']

    pqtl_props = {
        prop['name'] for prop in entry['subtypes'][1]['properties']
    }
    assert pqtl_props == {'beta'}


def test_genes_genes_merge_keeps_source_discriminator_only():
    curated = {
        'subtypes': [
            {
                'schema_file': 'genes_genes.Coxpresdb.json',
                'discriminators': {
                    'source': ['CoXPresdb'],
                    'method': ['coexpression'],
                    'label': ['co-expressed with'],
                },
                'properties': [
                    {'name': 'source', 'enum': ['CoXPresdb']},
                    {'name': 'z_score', 'type': 'number'},
                ],
            }
        ]
    }
    entry = build_curated_edge_collection_entry('genes_genes', curated)
    assert entry['subtypes'][0]['discriminators'] == {'source': ['CoXPresdb']}
    assert 'schema_file' not in entry['subtypes'][0]
    assert [p['name']
            for p in entry['subtypes'][0]['properties']] == ['z_score']


def test_merge_replaces_matching_edges_keeps_nodes_and_unknown_edges():
    graph_schema = {
        'Graph Schema': [],
        'Collection Schema': [
            {
                'collection_name': 'proteins',
                'collection_type': 'document',
                'document_properties': [{'name': 'name', 'type': 'str'}],
                'example_document': {'name': 'GATA1'},
            },
            {
                'collection_name': 'variants_proteins',
                'collection_type': 'edge',
                'edge_properties': [{'name': 'label', 'type': 'str'}],
                'example_edge': {'label': 'predicted allele-specific binding'},
            },
            {
                'collection_name': 'genes_genes_SCORPION_QA',
                'collection_type': 'edge',
                'edge_properties': [{'name': 'score', 'type': 'float'}],
                'example_edge': {'score': 1.0},
            },
        ],
    }

    merged = merge_curated_edge_schema(graph_schema, FIXTURE_CURATED)
    by_name = {
        entry['collection_name']: entry
        for entry in merged['Collection Schema']
    }

    assert by_name['proteins']['example_document']['name'] == 'GATA1'
    assert 'subtypes' in by_name['variants_proteins']
    assert 'example_edge' not in by_name['variants_proteins']
    assert by_name['genes_genes_SCORPION_QA']['example_edge']['score'] == 1.0
    # Original schema must not be mutated
    assert 'subtypes' not in graph_schema['Collection Schema'][1]


def test_apply_curated_edge_schema_sets_schema(tmp_path):
    class FakeGraph:
        def __init__(self):
            self.schema = {
                'Graph Schema': [],
                'Collection Schema': [
                    {
                        'collection_name': 'variants_proteins',
                        'collection_type': 'edge',
                        'edge_properties': [{'name': 'label', 'type': 'str'}],
                        'example_edge': {'label': 'x'},
                    }
                ],
            }

        def set_schema(self, schema):
            self.schema = schema

    curated_path = tmp_path / 'curated.json'
    curated_path.write_text(json.dumps(FIXTURE_CURATED))

    graph = FakeGraph()
    merged = apply_curated_edge_schema(graph, curated_path=curated_path)

    assert 'subtypes' in merged['Collection Schema'][0]
    assert 'subtypes' in graph.schema['Collection Schema'][0]
    subtype_props = merged['Collection Schema'][0]['subtypes'][0]['properties']
    assert all('example' not in prop for prop in subtype_props)
