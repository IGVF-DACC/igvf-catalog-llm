import pytest
from prompt_template import AQL_GENERATION_TEMPLATE, AQL_GENERATION_PROMPT, get_aql_generation_prompt
from constants import DEFAULT_LIMIT


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


def test_get_aql_generation_prompt_page_0():
    """Test prompt generation with page 0."""
    prompt = get_aql_generation_prompt(page=0)
    aql_examples = 'FOR doc IN genes RETURN doc'
    user_input = 'Show me all genes'

    formatted_prompt = prompt.format(
        aql_examples=aql_examples,
        user_input=user_input
    )

    assert 'Current page: 0' in formatted_prompt
    assert f'Offset: 0' in formatted_prompt
    assert f'Limit: {DEFAULT_LIMIT}' in formatted_prompt
    assert f'LIMIT 0, {DEFAULT_LIMIT}' in formatted_prompt


def test_get_aql_generation_prompt_page_1():
    """Test prompt generation with page 1."""
    prompt = get_aql_generation_prompt(page=1)
    aql_examples = 'FOR doc IN genes RETURN doc'
    user_input = 'Show me all genes'

    formatted_prompt = prompt.format(
        aql_examples=aql_examples,
        user_input=user_input
    )

    assert 'Current page: 1' in formatted_prompt
    offset = DEFAULT_LIMIT
    assert f'Offset: {offset}' in formatted_prompt
    assert f'LIMIT {offset}, {DEFAULT_LIMIT}' in formatted_prompt
