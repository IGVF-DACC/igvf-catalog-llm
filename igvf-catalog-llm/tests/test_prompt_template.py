import pytest
from prompt_template import AQL_GENERATION_TEMPLATE, AQL_GENERATION_PROMPT


def test_prompt_template_format():
    """Test that the prompt template can be formatted with variables."""
    aql_examples = 'FOR doc IN genes RETURN doc'
    user_input = 'Show me all genes'

    formatted_prompt = AQL_GENERATION_PROMPT.format(
        aql_examples=aql_examples,
        user_input=user_input
    )

    assert aql_examples in formatted_prompt
    assert user_input in formatted_prompt
    assert 'Task: Generate an ArangoDB Query Language' in formatted_prompt
