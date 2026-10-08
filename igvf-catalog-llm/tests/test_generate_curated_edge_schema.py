import json
import sys
from pathlib import Path

# tests/ -> igvf-catalog-llm/ -> repo root
ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / 'scripts'
sys.path.insert(0, str(SCRIPTS))

from generate_curated_edge_schema import (  # noqa: E402
    build_curated_schema,
    default_github_ref,
    discriminator_fields_for,
    parse_edge_schema_file,
)

FIXTURES = Path(__file__).parent / 'fixtures' / 'edge_schemas'


def test_skips_edges_base():
    assert parse_edge_schema_file(FIXTURES / 'edges.base.json') is None


def test_skips_excluded_ontology_terms_collection():
    assert parse_edge_schema_file(
        FIXTURES / 'ontology_terms_ontology_terms.Ontology.json'
    ) is None


def test_parse_asb_subtype_discriminators():
    subtype = parse_edge_schema_file(FIXTURES / 'variants_proteins.ASB.json')
    assert subtype['db_collection_name'] == 'variants_proteins'
    assert subtype['discriminators'] == {
        'method': ['ADASTRA'],
        'source': ['ADASTRA'],
        'label': ['allele-specific binding'],
    }
    assert 'required' not in subtype
    prop_names = {prop['name'] for prop in subtype['properties']}
    assert 'motif_fc' in prop_names
    assert 'method' in prop_names


def test_genes_genes_discriminators_are_source_only():
    assert discriminator_fields_for('genes_genes') == ('source',)
    subtype = parse_edge_schema_file(FIXTURES / 'genes_genes.Coxpresdb.json')
    assert subtype['discriminators'] == {'source': ['CoXPresdb']}


def test_build_curated_schema_skips_single_subtype_and_excluded(tmp_path):
    curated = build_curated_schema(FIXTURES, source='fixtures')
    # variants_proteins (2), genes_genes (2); variants_genes (1) omitted;
    # ontology_terms_ontology_terms excluded
    assert curated['collection_count'] == 2
    assert curated['schema_count'] == 4
    assert 'variants_genes' not in curated['collections']
    assert 'ontology_terms_ontology_terms' not in curated['collections']

    variants_proteins = curated['collections']['variants_proteins']
    assert len(variants_proteins['subtypes']) == 2
    for subtype in variants_proteins['subtypes']:
        assert set(subtype['discriminators']) <= {'method', 'source', 'label'}
        assert 'required' not in subtype

    genes_genes = curated['collections']['genes_genes']
    assert len(genes_genes['subtypes']) == 2
    for subtype in genes_genes['subtypes']:
        assert list(subtype['discriminators'].keys()) == ['source']


def test_cli_writes_output(tmp_path):
    output = tmp_path / 'curated.json'
    from generate_curated_edge_schema import main

    assert main(['--schemas-dir', str(FIXTURES), '--output', str(output)]) == 0
    data = json.loads(output.read_text())
    assert 'variants_proteins' in data['collections']
    assert 'genes_genes' in data['collections']
    assert 'variants_genes' not in data['collections']
    assert 'ontology_terms_ontology_terms' not in data['collections']
    assert data['schema_count'] == 4


def test_default_github_ref_uses_env(monkeypatch):
    monkeypatch.delenv('IGVF_CATALOG_SCHEMA_REF', raising=False)
    assert default_github_ref() == 'dev'
    monkeypatch.setenv('IGVF_CATALOG_SCHEMA_REF', 'main')
    assert default_github_ref() == 'main'
