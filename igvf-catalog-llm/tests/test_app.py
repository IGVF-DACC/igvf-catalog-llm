import pytest
import os
import json
from unittest.mock import Mock, patch, MagicMock
from app import app, initialize_arango_graph, initialize_collection_names, build_response, ask_llm, generate_aql, extract_aql, apply_aql_limit, get_updated_graph, limiter
from constants import MAX_AQL_GENERATION_ATTEMPTS, MAX_AQL_LIMIT, QUERY_AQL_LIMIT


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    limiter.enabled = False
    with app.test_client() as client:
        yield client
    limiter.enabled = True


# Environment variables are set in conftest.py for app.py import


def test_initialize_collection_names():
    """Test collection names initialization."""
    collection_schema = [
        {'collection_name': 'genes'},
        {'collection_name': 'variants'},
        {'collection_name': 'diseases'}
    ]
    result = initialize_collection_names(collection_schema)
    assert result == ['genes', 'variants', 'diseases']


def test_initialize_collection_names_empty():
    """Test collection names initialization with empty schema."""
    result = initialize_collection_names([])
    assert result == []


def test_build_response():
    """Test response building function."""
    block = {
        'result': 'test result',
        'aql_query': 'FOR doc IN collection RETURN doc',
        'aql_examples': 'should be excluded',
        'user_input': 'should be excluded'
    }
    result = build_response(block)

    assert 'result' in result
    assert 'aql_query' in result
    assert 'aql_examples' not in result
    assert 'user_input' not in result
    assert result['title'] == 'IGVF Catalog LLM Query'


def test_get_updated_graph():
    """Test graph update function."""
    mock_graph = Mock()
    mock_graph.schema = {'Collection Schema': []}

    collection_schema = [
        {'collection_name': 'genes', 'properties': ['id', 'name']},
        {'collection_name': 'variants', 'properties': ['id', 'position']},
        {'collection_name': 'diseases', 'properties': ['id', 'name']}
    ]

    selected_collection_names = ['genes', 'diseases']

    result = get_updated_graph(
        mock_graph, collection_schema, selected_collection_names)

    assert result == mock_graph
    assert len(result.schema['Collection Schema']) == 2
    assert result.schema['Collection Schema'][0]['collection_name'] == 'genes'
    assert result.schema['Collection Schema'][1]['collection_name'] == 'diseases'


def test_get_updated_graph_empty_selection():
    """Test graph update function with empty selection."""
    mock_graph = Mock()
    mock_graph.schema = {'Collection Schema': []}

    collection_schema = [
        {'collection_name': 'genes', 'properties': ['id', 'name']}
    ]

    selected_collection_names = []

    result = get_updated_graph(
        mock_graph, collection_schema, selected_collection_names)

    assert result == mock_graph
    assert len(result.schema['Collection Schema']) == 0


def test_get_updated_graph_nonexistent_collection():
    """Test graph update function with nonexistent collection."""
    mock_graph = Mock()
    mock_graph.schema = {'Collection Schema': []}

    collection_schema = [
        {'collection_name': 'genes', 'properties': ['id', 'name']}
    ]

    selected_collection_names = ['nonexistent']

    result = get_updated_graph(
        mock_graph, collection_schema, selected_collection_names)

    assert result == mock_graph
    assert len(result.schema['Collection Schema']) == 0


@patch('app.select_collections')
@patch('app.get_updated_graph')
@patch('app.ArangoGraphQAChain')
@patch('app.get_openai_callback')
def test_ask_llm_success(mock_callback, mock_chain_class, mock_get_graph, mock_select_collections):
    """Test successful LLM query."""
    # Mock dependencies
    mock_select_collections.return_value = ['genes']
    mock_graph = Mock()
    mock_get_graph.return_value = mock_graph

    mock_chain = Mock()
    mock_chain_class.from_llm.return_value = mock_chain
    mock_chain.invoke.return_value = {
        'result': 'test result',
        'aql_query': 'FOR doc IN genes RETURN doc'
    }

    mock_cb = Mock()
    mock_callback.return_value.__enter__.return_value = mock_cb
    mock_callback.return_value.__exit__.return_value = None

    # Mock global variables
    with patch('app.collection_names', ['genes', 'variants']), \
            patch('app.graph', Mock()), \
            patch('app.collection_schema', [{'collection_name': 'genes'}]), \
            patch('app.model', Mock()), \
            patch('app.AQL_GENERATION_PROMPT', 'test prompt'), \
            patch('app.AQL_EXAMPLES', 'test examples'):

        result = ask_llm('test question')

        # Verify chain configuration
        mock_chain_class.from_llm.assert_called_once()
        call_args = mock_chain_class.from_llm.call_args
        assert call_args[1]['aql_generation_prompt'] == 'test prompt'
        assert call_args[1]['graph'] == mock_graph
        assert call_args[1]['verbose'] == True
        assert call_args[1]['allow_dangerous_requests'] == True

        # Verify chain properties
        assert mock_chain.top_k == QUERY_AQL_LIMIT
        assert mock_chain.max_aql_generation_attempts == MAX_AQL_GENERATION_ATTEMPTS
        assert mock_chain.return_aql_query == True
        assert mock_chain.return_aql_result == True
        assert mock_chain.aql_examples == 'test examples'

        # Verify chain invocation
        mock_chain.invoke.assert_called_once_with({
            'user_input': 'test question',
            'query': 'test question'
        })

        assert result == {
            'result': 'test result',
            'aql_query': 'FOR doc IN genes RETURN doc'
        }


def test_extract_aql_from_fenced_block():
    """Test AQL extraction from a fenced code block."""
    output = '```aql\nFOR doc IN genes RETURN doc\n```'
    assert extract_aql(output) == 'FOR doc IN genes RETURN doc'


def test_extract_aql_invalid_response():
    """Test AQL extraction returns None when no query is present."""
    assert extract_aql('I cannot help with that request.') is None


def test_extract_aql_unfenced_query():
    """Test AQL extraction accepts a query without code fences."""
    output = 'FOR doc IN genes RETURN doc'
    assert extract_aql(output) == output


@pytest.mark.parametrize('aql_query,limit,offset,expected', [
    (
        'FOR doc IN genes RETURN doc',
        100,
        0,
        'FOR doc IN genes LIMIT 0, 100 RETURN doc',
    ),
    (
        'FOR doc IN genes LIMIT 5 RETURN doc',
        100,
        0,
        'FOR doc IN genes LIMIT 0, 100 RETURN doc',
    ),
    (
        'FOR doc IN genes LIMIT 0, 5 RETURN doc',
        50,
        50,
        'FOR doc IN genes LIMIT 50, 50 RETURN doc',
    ),
    (
        'RETURN LENGTH(genes)',
        100,
        0,
        'RETURN LENGTH(genes)',
    ),
])
def test_apply_aql_limit(aql_query, limit, offset, expected):
    """Test LIMIT rewrite for /aql generation."""
    assert apply_aql_limit(aql_query, limit=limit, offset=offset) == expected


@patch('app.select_collections')
@patch('app.get_updated_graph')
@patch('app.ArangoGraphQAChain')
@patch('app.get_openai_callback')
@patch('app.get_aql_examples')
@patch('app.get_aql_generation_prompt')
def test_generate_aql_does_not_invoke_chain(
        mock_get_prompt, mock_get_examples, mock_callback, mock_chain_class,
        mock_get_graph, mock_select_collections):
    """Test generate_aql uses aql_generation_chain and does not run the full QA chain."""
    mock_select_collections.return_value = ['genes']
    mock_graph = Mock()
    mock_graph.schema = {'Collection Schema': []}
    mock_get_graph.return_value = mock_graph
    mock_get_prompt.return_value = 'aql only prompt'
    mock_get_examples.return_value = 'aql only examples'

    mock_chain = Mock()
    mock_chain_class.from_llm.return_value = mock_chain
    mock_chain.aql_generation_chain.run.return_value = (
        '```aql\nFOR doc IN genes RETURN doc\n```'
    )

    mock_cb = Mock()
    mock_callback.return_value.__enter__.return_value = mock_cb
    mock_callback.return_value.__exit__.return_value = None

    with patch('app.collection_names', ['genes', 'variants']), \
            patch('app.graph', Mock()), \
            patch('app.collection_schema', [{'collection_name': 'genes'}]), \
            patch('app.model', Mock()):

        result = generate_aql('test question')

        mock_get_prompt.assert_called_once_with(limit=100, offset=0)
        mock_get_examples.assert_called_once_with(limit=100, offset=0)
        mock_chain_class.from_llm.assert_called_once()
        assert mock_chain_class.from_llm.call_args[1]['aql_generation_prompt'] == 'aql only prompt'
        mock_chain.aql_generation_chain.run.assert_called_once_with({
            'adb_schema': mock_graph.schema,
            'aql_examples': 'aql only examples',
            'user_input': 'test question',
        })
        mock_chain.invoke.assert_not_called()
        mock_graph.query.assert_not_called()

        assert result == {
            'query': 'test question',
            'aql_query': 'FOR doc IN genes LIMIT 0, 100 RETURN doc'
        }
        assert 'result' not in result


@patch('app.select_collections')
@patch('app.get_updated_graph')
@patch('app.ArangoGraphQAChain')
@patch('app.get_openai_callback')
@patch('app.get_aql_examples')
@patch('app.get_aql_generation_prompt')
def test_generate_aql_invalid_response_does_not_raise(
        mock_get_prompt, mock_get_examples, mock_callback, mock_chain_class,
        mock_get_graph, mock_select_collections):
    """Test generate_aql returns an error payload when no AQL is produced."""
    mock_select_collections.return_value = ['genes']
    mock_graph = Mock()
    mock_graph.schema = {'Collection Schema': []}
    mock_get_graph.return_value = mock_graph
    mock_get_prompt.return_value = 'aql only prompt'
    mock_get_examples.return_value = 'aql only examples'

    mock_chain = Mock()
    mock_chain_class.from_llm.return_value = mock_chain
    mock_chain.aql_generation_chain.run.return_value = (
        'I cannot help with that request.'
    )
    mock_callback.return_value.__enter__.return_value = Mock()
    mock_callback.return_value.__exit__.return_value = None

    with patch('app.collection_names', ['genes']), \
            patch('app.graph', Mock()), \
            patch('app.collection_schema', [{'collection_name': 'genes'}]), \
            patch('app.model', Mock()):

        result = generate_aql('test question')

        assert result['query'] == 'test question'
        assert result['aql_query'] is None
        assert 'Response is Invalid' in result['error']
        assert 'result' not in result


def test_health_check_success(client):
    """Test successful health check."""
    with patch('app.arango_healthy', True), \
            patch('app.model', Mock()):
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'OK'
        assert data['arangodb'] == 'OK'
        assert data['llm'] == 'OK'


def test_health_check_arango_error(client):
    """Test health check with ArangoDB error."""
    with patch('app.arango_healthy', False), \
            patch('app.arango_error', 'Connection failed'), \
            patch('app.model', Mock()):
        response = client.get('/health')
        assert response.status_code == 503
        data = json.loads(response.data)
        assert data['status'] == 'ERROR'
        assert 'ERROR: Connection failed' in data['arangodb']


def test_health_check_llm_error(client):
    """Test health check with LLM error."""
    with patch('app.arango_healthy', True), \
            patch('app.model', None):
        response = client.get('/health')
        assert response.status_code == 503
        data = json.loads(response.data)
        assert data['status'] == 'ERROR'
        assert data['llm'] == 'ERROR: LLM not initialized'


def test_query_missing_data(client):
    """Test query endpoint with missing data."""
    response = client.post('/query', json={})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    assert 'password and query are required' in data['error']


def test_query_wrong_password(client):
    """Test query endpoint with wrong password."""
    response = client.post('/query', json={
        'password': 'wrong_password',
        'query': 'test query'
    })
    assert response.status_code == 403
    data = json.loads(response.data)
    assert 'error' in data
    assert 'wrong password' in data['error']


def test_query_correct_password(client):
    """Test query endpoint with correct password."""
    with patch('app.model', Mock()), \
            patch('app.graph', Mock()), \
            patch('app.collection_schema', Mock()), \
            patch('app.ask_llm') as mock_ask_llm:

        mock_ask_llm.return_value = {
            'result': 'test result',
            'aql_query': 'FOR doc IN collection RETURN doc'
        }

        response = client.post('/query', json={
            'password': 'test_password',
            'query': 'test query'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'result' in data
        assert 'aql_query' in data
        assert data['title'] == 'IGVF Catalog LLM Query'


def test_query_service_unavailable(client):
    """Test query endpoint when services are not available."""
    with patch('app.model', None), \
            patch('app.graph', None), \
            patch('app.collection_schema', None):

        response = client.post('/query', json={
            'password': 'test_password',
            'query': 'test query'
        })

        assert response.status_code == 503
        data = json.loads(response.data)
        assert 'error' in data
        assert 'LLM or ArangoDB graph not initialized properly' in data['error']


def test_query_exception_handling(client):
    """Test query endpoint exception handling."""
    with patch('app.model', Mock()), \
            patch('app.graph', Mock()), \
            patch('app.collection_schema', Mock()), \
            patch('app.ask_llm') as mock_ask_llm:

        mock_ask_llm.side_effect = Exception('Test error')

        response = client.post('/query', json={
            'password': 'test_password',
            'query': 'test query'
        })

        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Test error' in data['error']
        assert data['query'] == 'test query'


def test_query_value_error_invalid_response_handling(client):
    """Test query endpoint special ValueError handling for invalid responses."""
    with patch('app.model', Mock()), \
            patch('app.graph', Mock()), \
            patch('app.collection_schema', Mock()), \
            patch('app.ask_llm') as mock_ask_llm:

        mock_ask_llm.side_effect = ValueError(
            'Response is Invalid: I cannot help with that request.')

        response = client.post('/query', json={
            'password': 'test_password',
            'query': 'test query'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['title'] == 'IGVF Catalog LLM Query'
        assert data['query'] == 'test query'
        assert data['error'] == 'Response is Invalid: I cannot help with that request.'
        assert data['result'] == "Sorry, I can't help with this right now."


def test_query_value_error_returns_422(client):
    """Test query endpoint generic ValueError handling."""
    with patch('app.model', Mock()), \
            patch('app.graph', Mock()), \
            patch('app.collection_schema', Mock()), \
            patch('app.ask_llm') as mock_ask_llm:

        mock_ask_llm.side_effect = ValueError('validation failed')

        response = client.post('/query', json={
            'password': 'test_password',
            'query': 'test query'
        })

        assert response.status_code == 422
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error'] == 'validation failed'
        assert data['query'] == 'test query'


def test_aql_missing_data(client):
    """Test aql endpoint with missing data."""
    response = client.post('/aql', json={})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    assert 'password and query are required' in data['error']


def test_aql_wrong_password(client):
    """Test aql endpoint with wrong password."""
    response = client.post('/aql', json={
        'password': 'wrong_password',
        'query': 'test query'
    })
    assert response.status_code == 403
    data = json.loads(response.data)
    assert 'error' in data
    assert 'wrong password' in data['error']


def test_aql_correct_password(client):
    """Test aql endpoint with correct password."""
    with patch('app.model', Mock()), \
            patch('app.graph', Mock()), \
            patch('app.collection_schema', Mock()), \
            patch('app.generate_aql') as mock_generate_aql:

        mock_generate_aql.return_value = {
            'query': 'test query',
            'aql_query': 'FOR doc IN collection RETURN doc'
        }

        response = client.post('/aql', json={
            'password': 'test_password',
            'query': 'test query'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['query'] == 'test query'
        assert data['aql_query'] == 'FOR doc IN collection RETURN doc'
        assert 'result' not in data
        assert 'aql_result' not in data
        assert data['title'] == 'IGVF Catalog LLM Query'
        mock_generate_aql.assert_called_once_with(
            'test query', limit=100, offset=0)


def test_aql_service_unavailable(client):
    """Test aql endpoint when services are not available."""
    with patch('app.model', None), \
            patch('app.graph', None), \
            patch('app.collection_schema', None):

        response = client.post('/aql', json={
            'password': 'test_password',
            'query': 'test query'
        })

        assert response.status_code == 503
        data = json.loads(response.data)
        assert 'error' in data
        assert 'LLM or ArangoDB graph not initialized properly' in data['error']


def test_aql_exception_handling(client):
    """Test aql endpoint exception handling."""
    with patch('app.model', Mock()), \
            patch('app.graph', Mock()), \
            patch('app.collection_schema', Mock()), \
            patch('app.generate_aql') as mock_generate_aql:

        mock_generate_aql.side_effect = Exception('Test error')

        response = client.post('/aql', json={
            'password': 'test_password',
            'query': 'test query'
        })

        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Test error' in data['error']
        assert data['query'] == 'test query'


def test_aql_value_error_invalid_response_handling(client):
    """Test aql endpoint special ValueError handling for invalid responses."""
    with patch('app.model', Mock()), \
            patch('app.graph', Mock()), \
            patch('app.collection_schema', Mock()), \
            patch('app.generate_aql') as mock_generate_aql:

        mock_generate_aql.side_effect = ValueError(
            'Response is Invalid: I cannot help with that request.')

        response = client.post('/aql', json={
            'password': 'test_password',
            'query': 'test query'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['title'] == 'IGVF Catalog LLM Query'
        assert data['query'] == 'test query'
        assert data['error'] == 'Response is Invalid: I cannot help with that request.'
        assert 'result' not in data


def test_aql_value_error_returns_422(client):
    """Test aql endpoint generic ValueError handling."""
    with patch('app.model', Mock()), \
            patch('app.graph', Mock()), \
            patch('app.collection_schema', Mock()), \
            patch('app.generate_aql') as mock_generate_aql:

        mock_generate_aql.side_effect = ValueError('validation failed')

        response = client.post('/aql', json={
            'password': 'test_password',
            'query': 'test query'
        })

        assert response.status_code == 422
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error'] == 'validation failed'
        assert data['query'] == 'test query'


def test_aql_accepts_limit_and_page(client):
    """Test aql endpoint passes limit and page offset to generate_aql."""
    with patch('app.model', Mock()), \
            patch('app.graph', Mock()), \
            patch('app.collection_schema', Mock()), \
            patch('app.generate_aql') as mock_generate_aql:

        mock_generate_aql.return_value = {
            'query': 'test query',
            'aql_query': 'FOR doc IN genes LIMIT 50, 50 RETURN doc'
        }

        response = client.post('/aql', json={
            'password': 'test_password',
            'query': 'test query',
            'limit': 50,
            'page': 1
        })

        assert response.status_code == 200
        mock_generate_aql.assert_called_once_with(
            'test query', limit=50, offset=50)


@pytest.mark.parametrize('payload,expected_error', [
    ({'limit': 0}, f'limit must be between 1 and {MAX_AQL_LIMIT}'),
    ({'limit': MAX_AQL_LIMIT + 1}, f'limit must be between 1 and {MAX_AQL_LIMIT}'),
    ({'page': -1}, 'page must be a non-negative integer'),
    ({'limit': 'abc'}, 'limit and page must be integers'),
])
def test_aql_invalid_pagination(client, payload, expected_error):
    """Test aql endpoint rejects invalid limit and page values."""
    body = {
        'password': 'test_password',
        'query': 'test query',
    }
    body.update(payload)
    response = client.post('/aql', json=body)
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['error'] == expected_error
