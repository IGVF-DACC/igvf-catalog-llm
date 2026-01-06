import pytest
import os
import json
from unittest.mock import Mock, patch
from app import app, initialize_arango_graph, initialize_collection_names, build_response, ask_llm, get_updated_graph, add_limit_to_aql, initialize_llm
from constants import DEFAULT_LIMIT


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


# Environment variables are set in conftest.py for app.py import


def test_initialize_collection_names():
    """Test collection names initialization."""
    collection_schema = [
        {'name': 'genes'},
        {'name': 'variants'},
        {'name': 'diseases'}
    ]
    result = initialize_collection_names(collection_schema)
    assert result == ['genes', 'variants', 'diseases']


@pytest.mark.parametrize('execute_aql_query,expected_result', [
    (False, None),
    (True, 'test result')
])
def test_build_response(execute_aql_query, expected_result):
    """Test response building function for both execute_aql_query modes."""
    if execute_aql_query:
        mock_aql_query = Mock()
        mock_aql_query.content = 'FOR doc IN collection RETURN doc'
        mock_result = Mock()
        mock_result.content = 'test result'
        block = {
            'query': 'test query',
            'aql_query': mock_aql_query,
            'result': mock_result,
            'aql_result': []
        }
    else:
        block = {
            'query': 'test query',
            'result': 'FOR doc IN collection RETURN doc',
            'aql_result': []
        }

    result = build_response(block, execute_aql_query=execute_aql_query)

    assert 'result' in result
    assert result['result'] == expected_result
    assert 'aql_query' in result
    if execute_aql_query:
        assert result['aql_query'] == 'FOR doc IN collection RETURN doc'
    assert 'aql_result' in result
    assert 'query' in result
    assert result['title'] == 'IGVF Catalog LLM Query'


def test_get_updated_graph():
    """Test graph update function with normal and edge cases."""
    mock_graph = Mock()
    mock_graph.schema = {'collection_schema': []}

    collection_schema = [
        {'name': 'genes', 'properties': ['id', 'name']},
        {'name': 'variants', 'properties': ['id', 'position']},
        {'name': 'diseases', 'properties': ['id', 'name']}
    ]

    # Test normal case
    selected_collection_names = ['genes', 'diseases']
    result = get_updated_graph(
        mock_graph, collection_schema, selected_collection_names)
    assert result == mock_graph
    assert len(result.schema['collection_schema']) == 2
    assert result.schema['collection_schema'][0]['name'] == 'genes'
    assert result.schema['collection_schema'][1]['name'] == 'diseases'

    # Test nonexistent collection
    selected_collection_names = ['nonexistent']
    result = get_updated_graph(
        mock_graph, collection_schema, selected_collection_names)
    assert result == mock_graph
    assert len(result.schema['collection_schema']) == 0


@patch('app.select_collections')
@patch('app.get_updated_graph')
@patch('app.ArangoGraphQAChain')
@patch('app.get_openai_callback')
@patch('app.get_aql_generation_prompt')
@patch('app.db')
def test_ask_llm(mock_db, mock_get_prompt, mock_callback, mock_chain_class, mock_get_graph, mock_select_collections):
    """Test ask_llm function for both execute_aql_query modes."""
    # Mock dependencies
    mock_select_collections.return_value = ['genes']
    mock_graph = Mock()
    mock_get_graph.return_value = mock_graph
    mock_prompt = Mock()
    mock_get_prompt.return_value = mock_prompt
    mock_chain = Mock()
    mock_chain_class.from_llm.return_value = mock_chain
    mock_cb = Mock()
    mock_callback.return_value.__enter__.return_value = mock_cb
    mock_callback.return_value.__exit__.return_value = None

    # Test execute_aql_query=False
    mock_chain.invoke.return_value = {
        'result': 'FOR doc IN genes RETURN doc',
        'aql_query': Mock(content='FOR doc IN genes RETURN doc')
    }
    mock_db.aql.execute.return_value = []

    with patch('app.collection_names', ['genes', 'variants']), \
            patch('app.graph', Mock()), \
            patch('app.collection_schema', [{'collection_name': 'genes'}]), \
            patch('app.model', Mock()), \
            patch('app.AQL_EXAMPLES', 'test examples'):

        result = ask_llm('test question', execute_aql_query=False)
        assert 'result' in result
        assert 'aql_result' in result
        mock_get_prompt.assert_called_with(page=0)

    # Test execute_aql_query=True with page=1
    mock_aql_query = Mock()
    mock_aql_query.content = 'FOR doc IN genes RETURN doc'
    mock_result = Mock()
    mock_result.content = 'test result'
    mock_chain.invoke.return_value = {
        'aql_query': mock_aql_query,
        'result': mock_result,
        'aql_result': [{'gene': 'SAMD11'}]
    }

    with patch('app.collection_names', ['genes', 'variants']), \
            patch('app.graph', Mock()), \
            patch('app.collection_schema', [{'collection_name': 'genes'}]), \
            patch('app.model', Mock()), \
            patch('app.AQL_EXAMPLES', 'test examples'):

        result = ask_llm('test question', execute_aql_query=True, page=1)
        assert 'aql_query' in result
        assert 'aql_result' in result
        assert result['aql_result'] == [{'gene': 'SAMD11'}]
        mock_get_prompt.assert_called_with(page=1)


@pytest.mark.parametrize('arango_healthy,arango_error,model,expected_status,expected_code', [
    (True, None, Mock(), 'OK', 200),
    (False, 'Connection failed', Mock(), 'ERROR', 503),
    (True, None, None, 'ERROR', 503)
])
def test_health_check(client, arango_healthy, arango_error, model, expected_status, expected_code):
    """Test health check endpoint with various scenarios."""
    with patch('app.arango_healthy', arango_healthy), \
            patch('app.arango_error', arango_error), \
            patch('app.model', model):
        response = client.get('/health')
        assert response.status_code == expected_code
        data = json.loads(response.data)
        assert data['status'] == expected_status


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


@pytest.mark.parametrize('page,expected_page', [
    (None, 0),
    (0, 0),
    (1, 1)
])
def test_query_endpoint(client, page, expected_page):
    """Test query endpoint with correct password and various page values."""
    with patch('app.model', Mock()), \
            patch('app.graph', Mock()), \
            patch('app.collection_schema', Mock()), \
            patch('app.ask_llm') as mock_ask_llm, \
            patch('app.build_response') as mock_build_response:

        mock_response_data = {
            'query': 'test query',
            'aql_query': 'FOR doc IN collection RETURN doc',
            'aql_result': [],
            'result': None,
            'title': 'IGVF Catalog LLM Query'
        }
        mock_ask_llm.return_value = {
            'query': 'test query',
            'result': 'FOR doc IN collection RETURN doc',
            'aql_result': []
        }
        mock_build_response.return_value = mock_response_data

        json_data = {
            'password': 'test_password',
            'query': 'test query'
        }
        if page is not None:
            json_data['page'] = page

        response = client.post('/query', json=json_data)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'aql_query' in data
        assert data['title'] == 'IGVF Catalog LLM Query'
        mock_ask_llm.assert_called_once()
        call_args = mock_ask_llm.call_args
        assert call_args[0][0] == 'test query'
        assert call_args[0][2] == expected_page


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


@pytest.mark.parametrize('page_value,expected_error', [
    (-1, 'page must be a non-negative integer'),
    ('not_a_number', 'page must be a non-negative integer')
])
def test_query_invalid_page(client, page_value, expected_error):
    """Test query endpoint with invalid page parameter."""
    response = client.post('/query', json={
        'password': 'test_password',
        'query': 'test query',
        'page': page_value
    })

    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    assert expected_error in data['error']


@pytest.mark.parametrize('aql_query,page,should_have_limit,expected_limit', [
    ("FOR gene IN genes FILTER gene.name == 'SAMD11' RETURN gene",
     0, True, f'LIMIT 0, {DEFAULT_LIMIT}'),
    (f"FOR gene IN genes FILTER gene.name == 'SAMD11' LIMIT 0, {DEFAULT_LIMIT} RETURN gene",
     0, True, f'LIMIT 0, {DEFAULT_LIMIT}'),
    ('RETURN LENGTH(FOR gene IN genes RETURN gene)', 0, False, None),
    ('RETURN COUNT(FOR gene IN genes RETURN gene)', 0, False, None)
])
def test_add_limit_to_aql(aql_query, page, should_have_limit, expected_limit):
    """Test add_limit_to_aql function with various scenarios."""
    result = add_limit_to_aql(aql_query, page=page)

    if should_have_limit:
        assert 'LIMIT' in result
        if expected_limit:
            assert expected_limit in result
        if 'RETURN' in aql_query:
            assert result.find('LIMIT') < result.find('RETURN')
    else:
        # Count/aggregation queries should not have LIMIT
        assert result == aql_query
        assert 'LIMIT' not in result


@pytest.mark.parametrize('success,expected_healthy,expected_error', [
    (True, True, None),
    (False, False, 'Connection failed')
])
@patch('app.ArangoClient')
def test_initialize_arango_graph(mock_arango_client, success, expected_healthy, expected_error):
    """Test ArangoDB graph initialization for success and failure cases."""
    mock_client = Mock()
    mock_arango_client.return_value = mock_client

    if success:
        mock_db = Mock()
        mock_graph = Mock()
        mock_client.db.return_value = mock_db
        with patch('app.ArangoGraph', return_value=mock_graph), \
                patch('app.BACKEND_URL', 'https://test-db.example.com/'), \
                patch('app.DB_NAME', 'test_db'), \
                patch.dict(os.environ, {'CATALOG_USERNAME': 'test_user', 'CATALOG_PASSWORD': 'test_pass'}):

            graph, db, healthy, error = initialize_arango_graph()
            assert graph == mock_graph
            assert db == mock_db
            assert healthy == expected_healthy
            assert error is None
    else:
        mock_client.db.side_effect = Exception('Connection failed')
        with patch('app.BACKEND_URL', 'https://test-db.example.com/'), \
                patch('app.DB_NAME', 'test_db'), \
                patch.dict(os.environ, {'CATALOG_USERNAME': 'test_user', 'CATALOG_PASSWORD': 'test_pass'}):

            graph, db, healthy, error = initialize_arango_graph()
            assert graph is None
            assert db is None
            assert healthy == expected_healthy
            assert error == expected_error


@patch('app.ChatOpenAI')
def test_initialize_llm(mock_chat_openai):
    """Test LLM initialization."""
    mock_model = Mock()
    mock_chat_openai.return_value = mock_model

    with patch('app.OPENAI_MODEL', 'gpt-4.1'):
        result = initialize_llm()

        assert result == mock_model
        mock_chat_openai.assert_called_once_with(
            temperature=0, model_name='gpt-4.1')
