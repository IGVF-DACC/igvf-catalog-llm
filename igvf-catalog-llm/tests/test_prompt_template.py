import pytest
from prompt_template import AQL_GENERATION_TEMPLATE, AQL_GENERATION_PROMPT


class TestPromptTemplate:
    """Test prompt template functionality."""

    def test_template_contains_required_variables(self):
        """Test that template contains required variables."""
        template = AQL_GENERATION_TEMPLATE

        # Check for required variables
        assert '{aql_examples}' in template
        assert '{user_input}' in template

    def test_template_contains_instructions(self):
        """Test that template contains important instructions."""
        template = AQL_GENERATION_TEMPLATE

        # Check for key instructions
        assert 'ArangoDB Query Language (AQL)' in template
        assert 'WITH' in template
        assert 'LIMIT 5' in template
        assert '```' in template  # Backticks for code wrapping

    def test_template_contains_safety_instructions(self):
        """Test that template contains safety instructions."""
        template = AQL_GENERATION_TEMPLATE

        # Check for safety instructions
        assert 'Do not generate an AQL Query that removes or deletes any data' in template
        assert 'Under no circumstance should you generate an AQL Query that deletes any data' in template

    def test_template_contains_format_instructions(self):
        """Test that template contains formatting instructions."""
        template = AQL_GENERATION_TEMPLATE

        # Check for formatting instructions
        assert 'Return the `AQL Query` wrapped in 3 backticks' in template
        assert 'Do not include any text except the generated AQL Query' in template
        assert 'Do not provide explanations or apologies' in template

    def test_prompt_template_initialization(self):
        """Test that the prompt template is properly initialized."""
        assert AQL_GENERATION_PROMPT is not None
        assert hasattr(AQL_GENERATION_PROMPT, 'input_variables')
        assert hasattr(AQL_GENERATION_PROMPT, 'template')

    def test_prompt_template_variables(self):
        """Test that the prompt template has correct input variables."""
        expected_variables = ['aql_examples', 'user_input']
        assert AQL_GENERATION_PROMPT.input_variables == expected_variables

    def test_prompt_template_format(self):
        """Test that the prompt template can be formatted with variables."""
        aql_examples = 'FOR doc IN genes RETURN doc'
        user_input = 'Show me all genes'

        formatted_prompt = AQL_GENERATION_PROMPT.format(
            aql_examples=aql_examples,
            user_input=user_input
        )

        assert aql_examples in formatted_prompt
        assert user_input in formatted_prompt
        assert 'AQL Query:' in formatted_prompt

    def test_prompt_template_with_empty_examples(self):
        """Test prompt template formatting with empty AQL examples."""
        aql_examples = ''
        user_input = 'Show me all genes'

        formatted_prompt = AQL_GENERATION_PROMPT.format(
            aql_examples=aql_examples,
            user_input=user_input
        )

        assert user_input in formatted_prompt
        assert 'AQL Query Examples (Optional):' in formatted_prompt

    def test_prompt_template_structure(self):
        """Test that the prompt template has the expected structure."""
        template = AQL_GENERATION_TEMPLATE

        # Check for main sections
        assert 'Task:' in template
        assert 'Things you should do:' in template
        assert 'Things you should not do:' in template
        assert 'User Input:' in template
        assert 'AQL Query:' in template

    def test_prompt_template_schema_references(self):
        """Test that template references ArangoDB schema correctly."""
        template = AQL_GENERATION_TEMPLATE

        # Check for schema references
        assert 'ArangoDB Schema' in template
        assert 'Graph Schema' in template
        assert 'Collection Schema' in template
        assert 'JSON Object' in template
