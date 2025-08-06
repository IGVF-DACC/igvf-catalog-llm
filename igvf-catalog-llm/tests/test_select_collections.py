import pytest
from unittest.mock import patch, Mock
from select_collections import create_prompt, select_collections


class TestCreatePrompt:
    """Test prompt creation function."""

    def test_create_prompt_basic(self):
        """Test basic prompt creation."""
        input_text = 'What diseases are associated with gene PAH?'
        categories = ['genes', 'diseases_genes', 'variants']

        result = create_prompt(input_text, categories)

        assert input_text in result
        assert 'genes' in result
        assert 'diseases_genes' in result
        assert 'variants' in result
        assert 'category_names' in result
        assert 'json format' in result

    def test_create_prompt_empty_categories(self):
        """Test prompt creation with empty categories."""
        input_text = 'Test query'
        categories = []

        result = create_prompt(input_text, categories)

        assert input_text in result
        assert 'Categories:' in result
        assert 'category_names' in result

    def test_create_prompt_contains_examples(self):
        """Test that prompt contains the expected examples."""
        input_text = 'Test query'
        categories = ['genes', 'diseases']

        result = create_prompt(input_text, categories)

        # Check for example patterns
        assert 'what diseases are associated with gene PAH?' in result
        assert 'Tell me about gene PAH?' in result
        assert 'What does NEK5 interact with?' in result
        assert 'answer: [' in result


class TestSelectCollections:
    """Test collection selection function."""

    @patch('select_collections.openai')
    def test_select_collections_success(self, mock_openai):
        """Test successful collection selection."""
        # Mock the OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"category_names": ["genes", "diseases_genes"]}'
        mock_openai.chat.completions.create.return_value = mock_response

        query = 'What diseases are associated with gene PAH?'
        collection_names = ['genes', 'diseases_genes', 'variants']

        result = select_collections(query, collection_names)

        assert result == ['genes', 'diseases_genes']
        mock_openai.chat.completions.create.assert_called_once()

    @patch('select_collections.openai')
    def test_select_collections_single_category(self, mock_openai):
        """Test collection selection with single category."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"category_names": ["genes"]}'
        mock_openai.chat.completions.create.return_value = mock_response

        query = 'Tell me about gene PAH?'
        collection_names = ['genes', 'diseases_genes', 'variants']

        result = select_collections(query, collection_names)

        assert result == ['genes']

    @patch('select_collections.openai')
    def test_select_collections_invalid_json(self, mock_openai):
        """Test collection selection with invalid JSON response."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = 'Invalid JSON response'
        mock_openai.chat.completions.create.return_value = mock_response

        query = 'Test query'
        collection_names = ['genes', 'diseases']

        result = select_collections(query, collection_names)

        # Should return the raw output when JSON parsing fails
        assert result == 'Invalid JSON response'

    @patch('select_collections.openai')
    def test_select_collections_missing_category_names(self, mock_openai):
        """Test collection selection with missing category_names in response."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"other_field": ["genes"]}'
        mock_openai.chat.completions.create.return_value = mock_response

        query = 'Test query'
        collection_names = ['genes', 'diseases']

        result = select_collections(query, collection_names)

        # Should return the raw output when category_names is missing
        assert result == '{"other_field": ["genes"]}'

    @patch('select_collections.openai')
    def test_select_collections_api_error(self, mock_openai):
        """Test collection selection with API error."""
        mock_openai.chat.completions.create.side_effect = Exception(
            'API Error')

        query = 'Test query'
        collection_names = ['genes', 'diseases']

        with pytest.raises(Exception):
            select_collections(query, collection_names)

    @patch('select_collections.openai')
    def test_select_collections_verify_api_call(self, mock_openai):
        """Test that the API is called with correct parameters."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"category_names": ["genes"]}'
        mock_openai.chat.completions.create.return_value = mock_response

        query = 'Test query'
        collection_names = ['genes', 'diseases']

        select_collections(query, collection_names)

        # Verify the API call parameters
        call_args = mock_openai.chat.completions.create.call_args
        assert call_args[1]['model'] == 'gpt-4o'
        assert call_args[1]['temperature'] == 0
        assert call_args[1]['response_format'] == {'type': 'json_object'}
        assert len(call_args[1]['messages']) == 1
        assert call_args[1]['messages'][0]['role'] == 'user'
