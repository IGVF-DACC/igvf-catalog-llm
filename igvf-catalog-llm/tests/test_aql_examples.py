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
