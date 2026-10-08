from aql_examples import AQL_EXAMPLES, get_aql_examples
from constants import QUERY_AQL_LIMIT


def test_query_examples_use_limit_zero_five():
    """/query examples are the shared template with limit 5."""
    assert AQL_EXAMPLES == get_aql_examples(limit=QUERY_AQL_LIMIT, offset=0)
    assert 'LIMIT 0, 5' in AQL_EXAMPLES
    assert '{offset}' not in AQL_EXAMPLES
    assert '{limit}' not in AQL_EXAMPLES


def test_get_aql_examples_interpolates_limit():
    """Examples substitute offset and limit without leftover placeholders."""
    examples = get_aql_examples(limit=100, offset=0)
    assert 'LIMIT 0, 100' in examples
    assert '{offset}' not in examples
    assert '{limit}' not in examples
    assert 'LIMIT 5' not in examples
    assert '{ chr: v.chr, pos: v.pos}' in examples


def test_examples_prefer_selective_vertex_first():
    """Named-entity queries start from the selective vertex, not edge label."""
    examples = AQL_EXAMPLES
    assert 'FILTER o.name == \'cardiomyopathy\'' in examples
    assert 'FILTER d._to == o._id' in examples
    assert 'RETURN DOCUMENT(d._from)' in examples
    assert 'RETURN DOCUMENT(vg._from)' in examples
    assert 'OUTBOUND' not in examples
    # Multi-hop ontology walk may still use INBOUND; 1-hop neighbors use DOCUMENT
    assert 'INBOUND t ontology_terms_ontology_terms' in examples
    # More selective biosample filter before common label
    assert 'FILTER vg.biosample_term IN heartTerms AND vg.label == "eQTL"' in examples
