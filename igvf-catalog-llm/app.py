import os
import re
from flask import Flask, request, jsonify
from arango import ArangoClient
from langchain_arangodb import ArangoGraph, ArangoGraphQAChain
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from aql_examples import AQL_EXAMPLES
from select_collections import select_collections
from langchain_community.callbacks import get_openai_callback
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from constants import DEFAULT_LIMIT
from prompt_template import get_aql_generation_prompt
from constants import BACKEND_URL, DB_NAME, OPENAI_MODEL


# Initialize Flask app
app = Flask(__name__)


# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
limiter.init_app(app)


def initialize_arango_graph():
    # Connect to ArangoDB and initialize graph
    username = os.environ['CATALOG_USERNAME']
    password = os.environ['CATALOG_PASSWORD']
    client = ArangoClient(hosts=BACKEND_URL)
    try:
        db = client.db(DB_NAME, username=username, password=password)
        # Return graph, connection status (True), and no error
        return ArangoGraph(db), db, True, None
    except Exception as e:
        # Return None graph, connection status (False), and the error
        return None, None, False, str(e)


def initialize_collection_names(collection_schema):
    collection_names = [collection['name']
                        for collection in collection_schema]
    return collection_names


def initialize_llm():

    model = ChatOpenAI(temperature=0, model_name=OPENAI_MODEL)
    return model


def ask_llm(question, execute_aql_query=False, page=0):
    selected_collection_names = select_collections(question, collection_names)
    updated_graph = get_updated_graph(
        graph, collection_schema, selected_collection_names)
    # Get prompt template with pagination information for the current page
    aql_prompt = get_aql_generation_prompt(page=page)

    chain = ArangoGraphQAChain.from_llm(
        model,
        aql_generation_prompt=aql_prompt,
        graph=updated_graph,
        verbose=True,
        allow_dangerous_requests=True,
        force_read_only_query=True,
        aql_examples=AQL_EXAMPLES,
        top_k=DEFAULT_LIMIT,  # Set the maximum number of AQL Query Results
        execute_aql_query=execute_aql_query,
        return_aql_query=True,
        return_aql_result=True
    )

    # Specify the maximum amount of AQL Generation attempts that should be made
    # before returning an error
    chain.max_aql_generation_attempts = 5

    with get_openai_callback() as cb:
        input_data = {
            'user_input': question,
            'query': question,
        }
        response = chain.invoke(input_data)

        # Ensure LIMIT clause is present for pagination (fallback in case LLM doesn't include it)
        if not execute_aql_query:
            # When execute_aql_query is False, result contains the AQL query string
            aql = response['result']
            aql_with_limit = add_limit_to_aql(aql, page)
            response['result'] = aql_with_limit
            aql_result = db.aql.execute(aql_with_limit)
            # Convert Cursor to list for JSON serialization
            response['aql_result'] = list(aql_result)

    return response


graph, db, arango_healthy, arango_error = initialize_arango_graph()
if graph:
    collection_schema = graph.schema['collection_schema']
    collection_names = initialize_collection_names(collection_schema)
    model = initialize_llm()
else:
    collection_schema = None
    collection_names = []
    model = None
    print(f'Error initializing ArangoDB graph: {arango_error}')


def get_updated_graph(graph, collection_schema, selected_collection_names):
    collection_schema_updated = []
    for collection_name in selected_collection_names:
        for collection in collection_schema:
            if collection['name'] == collection_name:
                collection_schema_updated.append(collection)
                break
    updated_graph = graph
    updated_graph.schema['collection_schema'] = collection_schema_updated
    return updated_graph


def add_limit_to_aql(aql_query, page=0):
    """
    Add LIMIT clause to AQL query for pagination if it doesn't already exist.
    This is a fallback to ensure pagination is always applied, even if the LLM doesn't include it.
    If LIMIT already exists, leave it unchanged.
    Otherwise, add it before RETURN statement.
    Does NOT add LIMIT to count/aggregation queries (LENGTH, COUNT, SUM, AVG, etc.).
    """

    # Check if this is a count/aggregation query - don't add LIMIT to these
    count_aggregation_pattern = re.compile(
        r'\bRETURN\s+(LENGTH|COUNT|SUM|AVG|MIN|MAX|COLLECT|GROUP)\s*\(', re.IGNORECASE)
    if count_aggregation_pattern.search(aql_query):
        # This is a count/aggregation query - don't add LIMIT
        return aql_query

    # Check if LIMIT already exists (case-insensitive)
    # Pattern matches: whitespace + LIMIT + whitespace + digits + comma + optional whitespace + digits
    # This pattern will match even if RETURN immediately follows without space
    limit_pattern = re.compile(r'\s+LIMIT\s+\d+\s*,\s*\d+\s*', re.IGNORECASE)

    # Find all matches
    matches = list(limit_pattern.finditer(aql_query))
    if not matches:

        # No LIMIT found - add LIMIT clause before RETURN if RETURN exists
        # Find RETURN statement (case-insensitive)
        # Calculate offset and limit
        offset = page * DEFAULT_LIMIT
        limit_clause = f'LIMIT {offset}, {DEFAULT_LIMIT}'
        return_match = re.search(r'\bRETURN\b', aql_query, re.IGNORECASE)
        if return_match:
            # Insert LIMIT before RETURN with proper spacing
            return_pos = return_match.start()
            # Ensure there's a space before RETURN
            before_return = aql_query[:return_pos].rstrip()
            after_return = aql_query[return_pos:]
            aql_query = f'{before_return} {limit_clause} {after_return}'

    return aql_query


def build_response(block, execute_aql_query=False):
    """
    if return_aql_result, the block has those keys: user_input, query, result, aql_query, aql_result
    else, the block has those keys: user_input, query, result, aql_result
    """
    # Convert AIMessage objects to strings if any remain
    cleaned_block = {}
    cleaned_block['query'] = block['query']
    if execute_aql_query:
        cleaned_block['aql_result'] = block['aql_result']
        cleaned_block['aql_query'] = block['aql_query'].content
        cleaned_block['result'] = block['result'].content
    else:
        cleaned_block['aql_result'] = block['aql_result']
        cleaned_block['aql_query'] = block['result']
        cleaned_block['result'] = None

    cleaned_block['title'] = 'IGVF Catalog LLM Query'
    return cleaned_block

# Create Flask endpoint for querying


@app.route('/query', methods=['POST'])
@limiter.limit('10 per minute')
def query():
    data = request.get_json()
    if not data or 'password' not in data or 'query' not in data:
        return jsonify({'error': 'password and query are required'}), 400

    # Check password
    if data['password'] != os.environ.get('CATALOG_PASSWORD'):
        return jsonify({'error': 'wrong password'}), 403

    user_query = data['query']
    # Get page parameter, default to 0 (0-based pagination)
    page = data.get('page', 0)
    try:
        page = int(page)
        if page < 0:
            return jsonify({'error': 'page must be a non-negative integer'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'page must be a non-negative integer'}), 400

    if not model or not graph or not collection_schema:
        return jsonify({'error': 'LLM or ArangoDB graph not initialized properly'}), 503
    execute_aql_query = data.get('execute_aql_query', False)
    try:
        response = ask_llm(user_query, execute_aql_query, page)
        json_response = jsonify(build_response(response, execute_aql_query))
        return json_response
    except Exception as e:
        error = {
            'query': user_query,
            'error': str(e)
        }
        return jsonify(error), 500


# Create Flask endpoint for health check
@app.route('/health', methods=['GET'])
def healthcheck():
    if arango_healthy and model is not None:
        return jsonify({
            'status': 'OK',
            'arangodb': 'OK',
            'llm': 'OK',
            'backend_url': BACKEND_URL
        }), 200
    else:
        status = {'status': 'ERROR'}
        if not arango_healthy:
            status['arangodb'] = f'ERROR: {arango_error}'
        else:
            status['arangodb'] = 'OK'
        if model is None:
            status['llm'] = 'ERROR: LLM not initialized'
        else:
            status['llm'] = 'OK'
        return jsonify(status), 503


# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
