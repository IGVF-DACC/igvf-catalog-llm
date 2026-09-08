import json
import logging
import os
import re
from flask import Flask, request, jsonify
from flask.logging import default_handler
from arango import ArangoClient
from langchain_community.graphs import ArangoGraph
from langchain.chains import ArangoGraphQAChain
from langchain_openai import ChatOpenAI
from aql_examples import AQL_EXAMPLES, get_aql_examples
from select_collections import select_collections
from langchain_community.callbacks import get_openai_callback
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from constants import (
    AQL_CODE_BLOCK_PATTERN,
    AQL_COUNT_AGGREGATION_PATTERN,
    AQL_LIMIT_PATTERN,
    BACKEND_URL,
    DB_NAME,
    MAX_AQL_GENERATION_ATTEMPTS,
    MAX_AQL_LIMIT,
    OPENAI_MODEL,
    QUERY_AQL_LIMIT,
)
from prompt_template import (
    AQL_GENERATION_PROMPT,
    get_aql_generation_prompt,
)

# Initialize Flask app
app = Flask(__name__)
<<<<<<< HEAD
app.logger.setLevel(logging.INFO)
default_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    datefmt='%d/%b/%Y %H:%M:%S',
))
=======
>>>>>>> ece420f (add endpoint aql)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, storage_uri='memory://')
limiter.init_app(app)


def initialize_arango_graph():
    # Connect to ArangoDB and initialize graph

    username = os.environ['CATALOG_USERNAME']
    password = os.environ['CATALOG_PASSWORD']
    client = ArangoClient(hosts=BACKEND_URL)
    try:
        db = client.db(DB_NAME, username=username, password=password)
        # Return graph, connection status (True), and no error
        return ArangoGraph(db), True, None
    except Exception as e:
        # Return None graph, connection status (False), and the error
        return None, False, str(e)


def initialize_collection_names(collection_schema):
    collection_names = [collection['collection_name']
                        for collection in collection_schema]
    return collection_names


def initialize_llm():

    model = ChatOpenAI(temperature=0, model_name=OPENAI_MODEL)
    return model


def extract_aql(aql_generation_output):
    matches = AQL_CODE_BLOCK_PATTERN.findall(aql_generation_output)
    if matches:
        return matches[0].strip()
    stripped = (aql_generation_output or '').strip()
    if re.search(r'^\s*(WITH|FOR|LET|RETURN)\b', stripped, re.IGNORECASE):
        return stripped
    return None


def apply_aql_limit(aql_query, limit, offset=0):
    if AQL_COUNT_AGGREGATION_PATTERN.search(aql_query):
        return aql_query

    limit_clause = f'LIMIT {offset}, {limit}'
    if AQL_LIMIT_PATTERN.search(aql_query):
        return AQL_LIMIT_PATTERN.sub(limit_clause, aql_query, count=1)

    return_match = re.search(r'\bRETURN\b', aql_query, re.IGNORECASE)
    if return_match:
        before_return = aql_query[:return_match.start()].rstrip()
        after_return = aql_query[return_match.start():]
        return f'{before_return} {limit_clause} {after_return}'
    return aql_query


def _build_chain(updated_graph, aql_generation_prompt=None, aql_examples=None):
    if aql_generation_prompt is None:
        aql_generation_prompt = AQL_GENERATION_PROMPT
    if aql_examples is None:
        aql_examples = AQL_EXAMPLES
    chain = ArangoGraphQAChain.from_llm(
        model,
        aql_generation_prompt=aql_generation_prompt,
        graph=updated_graph,
        verbose=True,
        allow_dangerous_requests=True,
    )
    # Set the maximum number of AQL Query Results to return to 5
    # This avoids burning the LLM token limit on JSON results
    chain.top_k = QUERY_AQL_LIMIT
    # Specify the maximum amount of AQL Generation attempts that should be made
    # before returning an error
    chain.max_aql_generation_attempts = MAX_AQL_GENERATION_ATTEMPTS

    # Specify whether or not to return the AQL Query in the output dictionary
    # Use `chain("...")` instead of `chain.invoke("...")` to see this change
    chain.return_aql_query = True

    # Specify whether or not to return the AQL JSON Result in the output dictionary
    # Use `chain("...")` instead of `chain.invoke("...")` to see this change
    chain.return_aql_result = True
    # The AQL Examples modifier instructs the LLM to adapt its AQL-completion style
    # to the user's examples. These examples arepassed to the AQL Generation Prompt
    # Template to promote few-shot-learning.

    chain.aql_examples = aql_examples
    return chain


def _prepare_graph_for_question(question):
    selected_collection_names = select_collections(question, collection_names)
    return get_updated_graph(
        graph, collection_schema, selected_collection_names)


<<<<<<< HEAD
def _numeric(value, integer=False):
    try:
        return int(value) if integer else float(value)
    except (TypeError, ValueError):
        return 0 if integer else 0.0


def _log_openai_usage(cb, endpoint):
    app.logger.info(json.dumps({
        'event': 'openai_usage',
        'endpoint': endpoint,
        'model': OPENAI_MODEL,
        'total_tokens': _numeric(getattr(cb, 'total_tokens', 0), integer=True),
        'prompt_tokens': _numeric(getattr(cb, 'prompt_tokens', 0), integer=True),
        'prompt_tokens_cached': _numeric(
            getattr(cb, 'prompt_tokens_cached', 0), integer=True),
        'completion_tokens': _numeric(
            getattr(cb, 'completion_tokens', 0), integer=True),
        'reasoning_tokens': _numeric(
            getattr(cb, 'reasoning_tokens', 0), integer=True),
        'successful_requests': _numeric(
            getattr(cb, 'successful_requests', 0), integer=True),
        'total_cost_usd': _numeric(getattr(cb, 'total_cost', 0.0)),
    }))


=======
>>>>>>> ece420f (add endpoint aql)
def ask_llm(question):
    updated_graph = _prepare_graph_for_question(question)
    chain = _build_chain(updated_graph)
    with get_openai_callback() as cb:
        input_data = {
            'user_input': question,
            'query': question,
        }
        response = chain.invoke(input_data)
        _log_openai_usage(cb, 'query')
    return response


def generate_aql(question, limit=MAX_AQL_LIMIT, offset=0):
    updated_graph = _prepare_graph_for_question(question)
    aql_prompt = get_aql_generation_prompt(limit=limit, offset=offset)
    aql_examples = get_aql_examples(limit=limit, offset=offset)
    chain = _build_chain(
        updated_graph,
        aql_generation_prompt=aql_prompt,
        aql_examples=aql_examples,
    )
    with get_openai_callback() as cb:
<<<<<<< HEAD
        generation = chain.aql_generation_chain.invoke(
=======
        aql_generation_output = chain.aql_generation_chain.run(
>>>>>>> ece420f (add endpoint aql)
            {
                'adb_schema': updated_graph.schema,
                'aql_examples': aql_examples,
                'user_input': question,
            }
        )
<<<<<<< HEAD
        _log_openai_usage(cb, 'graph-query-generator')
    aql_generation_output = (
        generation['text'] if isinstance(generation, dict) else generation
    )
=======
        print(cb)
>>>>>>> ece420f (add endpoint aql)
    aql_query = extract_aql(aql_generation_output)
    if not aql_query:
        return {
            'query': question,
            'aql_query': None,
            'error': f'Response is Invalid: {aql_generation_output}',
        }
    return {
        'query': question,
        'aql_query': apply_aql_limit(
            aql_query,
            limit=limit,
            offset=offset,
        ),
    }


graph, arango_healthy, arango_error = initialize_arango_graph()
if graph:
    collection_schema = graph.schema['Collection Schema']
    collection_names = initialize_collection_names(collection_schema)
    model = initialize_llm()
else:
    collection_schema = None
    collection_names = []
    model = None
    app.logger.error('Error initializing ArangoDB graph: %s', arango_error)


def get_updated_graph(graph, collection_schema, selected_collection_names):
    collection_schema_updated = []
    for collection_name in selected_collection_names:
        for collection in collection_schema:
            if collection['collection_name'] == collection_name:
                collection_schema_updated.append(collection)
                break
    updated_graph = graph
    updated_graph.schema['Collection Schema'] = collection_schema_updated
    return updated_graph


def build_response(block):
    return {
        **{k: v for k, v in block.items() if k not in ['aql_examples', 'user_input']},
        'title': 'IGVF Catalog LLM Query',
    }
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

    if not model or not graph or not collection_schema:
        return jsonify({'error': 'LLM or ArangoDB graph not initialized properly'}), 503

    try:
        response = ask_llm(user_query)
        return jsonify(build_response(response))
    except ValueError as e:
        if 'Response is Invalid' in str(e):
            response = {
                'query': user_query,
                'error': str(e),
                'result': "Sorry, I can't help with this right now."
            }
            return jsonify(build_response(response))
        error = {
            'query': user_query,
            'error': str(e)
        }
        return jsonify(error), 422
    except Exception as e:
        error = {
            'query': user_query,
            'error': str(e)
        }
        return jsonify(error), 500


<<<<<<< HEAD
<<<<<<< HEAD
@app.route('/graph-query-generator', methods=['POST'])
@limiter.limit('10 per minute')
def graph_query_generator():
=======
@app.route('/aql', methods=['POST'])
@limiter.limit('10 per minute')
def aql():
>>>>>>> ece420f (add endpoint aql)
=======
@app.route('/graph-query-generator', methods=['POST'])
@limiter.limit('10 per minute')
def graph_query_generator():
>>>>>>> 2090e32 (rename endpoint)
    data = request.get_json()
    if not data or 'password' not in data or 'query' not in data:
        return jsonify({'error': 'password and query are required'}), 400

    if data['password'] != os.environ.get('CATALOG_PASSWORD'):
        return jsonify({'error': 'wrong password'}), 403

    user_query = data['query']
    try:
        limit = int(data.get('limit', MAX_AQL_LIMIT))
        page = int(data.get('page', 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'limit and page must be integers'}), 400
    if page < 0:
        return jsonify({'error': 'page must be a non-negative integer'}), 400
    if limit < 1 or limit > MAX_AQL_LIMIT:
        return jsonify({
            'error': f'limit must be between 1 and {MAX_AQL_LIMIT}'
        }), 400
    offset = page * limit

    if not model or not graph or not collection_schema:
        return jsonify({'error': 'LLM or ArangoDB graph not initialized properly'}), 503

    try:
        response = generate_aql(user_query, limit=limit, offset=offset)
        return jsonify(build_response(response))
    except ValueError as e:
        if 'Response is Invalid' in str(e):
            response = {
                'query': user_query,
                'error': str(e),
            }
            return jsonify(build_response(response))
        error = {
            'query': user_query,
            'error': str(e)
        }
        return jsonify(error), 422
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
