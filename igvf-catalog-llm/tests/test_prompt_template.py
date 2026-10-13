from constants import QUERY_AQL_LIMIT
from prompt_template import AQL_GENERATION_PROMPT, get_aql_generation_prompt


def test_query_prompt_uses_limit_zero_five():
    """/query prompt is the shared template with limit 5."""
    aql_examples = 'FOR doc IN genes LIMIT 0, 5 RETURN doc'
    user_input = 'Show me all genes'

    formatted_prompt = AQL_GENERATION_PROMPT.format(
        aql_examples=aql_examples,
        user_input=user_input
    )

    assert aql_examples in formatted_prompt
    assert user_input in formatted_prompt
    assert 'Task: Generate an ArangoDB Query Language' in formatted_prompt
    assert 'LIMIT 0, 5' in formatted_prompt
    assert 'offset=0' in formatted_prompt
    assert 'count=5' in formatted_prompt
    assert 'AQL performance / optimization' in formatted_prompt
    assert 'Never scan a large edge collection by `label`' in formatted_prompt
    assert 'Preferred shape (vertex first, indexed `method`, early LIMIT, DOCUMENT)' in formatted_prompt
    assert 'How to use edge `subtypes`' in formatted_prompt
    assert 'Multi-shape' in formatted_prompt
    assert 'discriminators' in formatted_prompt
    assert 'Do not mix fields from different subtypes' in formatted_prompt
    assert 'limited to shared handles' in formatted_prompt
    assert 'not again under `properties`' in formatted_prompt
    assert 'use `method` if that subtype' in formatted_prompt
    assert 'Prefer `method` because it is always indexed' in formatted_prompt
    assert 'vp.method == "ADASTRA"' in formatted_prompt
    assert 'Identifier lookup (nodes):' in formatted_prompt
    assert 'Do not use `uniprot_names` for a bare gene symbol' in formatted_prompt
    assert '"rs…" IN v.rsid' in formatted_prompt
    assert 'Do not nest' in formatted_prompt
    assert 'RETURN DOCUMENT(vp._from)' in formatted_prompt
    assert 'Avoid `INBOUND`/`OUTBOUND` for simple 1-hop lookups' in formatted_prompt
    assert '1-hop traversal — DO NOT' in formatted_prompt


def test_get_aql_generation_prompt_interpolates_limit():
    """Prompt interpolates limit and offset."""
    prompt = get_aql_generation_prompt(limit=100, offset=50)
    formatted_prompt = prompt.format(
        aql_examples='FOR doc IN genes LIMIT 50, 100 RETURN doc',
        user_input='Show me all genes'
    )

    assert 'LIMIT 50, 100' in formatted_prompt
    assert 'offset=50' in formatted_prompt
    assert 'count=100' in formatted_prompt


def test_query_prompt_matches_factory():
    query_prompt = get_aql_generation_prompt(limit=QUERY_AQL_LIMIT, offset=0)
    assert AQL_GENERATION_PROMPT.template == query_prompt.template
    assert AQL_GENERATION_PROMPT.partial_variables == query_prompt.partial_variables
