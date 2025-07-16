import os
from flask import Flask, request, jsonify
from arango import ArangoClient
from langchain_community.graphs import ArangoGraph
from langchain.chains import ArangoGraphQAChain
from langchain_openai import ChatOpenAI
from aql_examples import AQL_EXAMPLES
from select_collections import select_collections
from langchain_community.callbacks import get_openai_callback
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from prompt_template import AQL_GENERATION_PROMPT


# Initialize Flask app
app = Flask(__name__)

BACKEND_URL = os.environ.get('BACKEND_URL', 'https://db-dev.catalog.igvf.org/')
DB_NAME = 'igvf'
OPENAI_MODEL = 'gpt-4.1'

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
limiter.init_app(app)

def initialize_arango_graph():
    # Connect to ArangoDB and initialize graph

    username =  os.environ['CATALOG_USERNAME']
    password = os.environ['CATALOG_PASSWORD']
    client = ArangoClient(hosts=BACKEND_URL)
    try:
        db = client.db(DB_NAME, username=username, password=password)
        return ArangoGraph(db), True, None  # Return graph, connection status (True), and no error
    except Exception as e:
        return None, False, str(e)  # Return None graph, connection status (False), and the error


def initialize_collection_names(collection_schema):
    collection_names = [collection['collection_name']
                        for collection in collection_schema]
    return collection_names


def initialize_llm():

    model = ChatOpenAI(temperature=0, model_name=OPENAI_MODEL)
    return model


def ask_llm(question):
    selected_collection_names = select_collections(question, collection_names)
    updated_graph = get_updated_graph(
        graph, collection_schema, selected_collection_names)
    chain = ArangoGraphQAChain.from_llm(
        model,
        aql_generation_prompt=AQL_GENERATION_PROMPT,
        graph=updated_graph,
        verbose=True,
        allow_dangerous_requests=True,
    )
    # Set the maximum number of AQL Query Results to return to 5
    # This avoids burning the LLM token limit on JSON results
    chain.top_k = 5
    # Specify the maximum amount of AQL Generation attempts that should be made
    # before returning an error
    chain.max_aql_generation_attempts = 5

    # Specify whether or not to return the AQL Query in the output dictionary
    # Use `chain("...")` instead of `chain.invoke("...")` to see this change
    chain.return_aql_query = True

    # Specify whether or not to return the AQL JSON Result in the output dictionary
    # Use `chain("...")` instead of `chain.invoke("...")` to see this change
    chain.return_aql_result = True
    # The AQL Examples modifier instructs the LLM to adapt its AQL-completion style
    # to the user's examples. These examples arepassed to the AQL Generation Prompt
    # Template to promote few-shot-learning.

    chain.aql_examples = AQL_EXAMPLES
    with get_openai_callback() as cb:
        input_data = {
            'user_input': question,
            'query': question,
        }
        response = chain.invoke(input_data)
        print(cb)
    return response

graph, arango_healthy, arango_error = initialize_arango_graph()
if graph:
    collection_schema = graph.schema['Collection Schema']
    collection_names = initialize_collection_names(collection_schema)
    model = initialize_llm()
else:
    collection_schema = None
    collection_names = []
    model = None
    print(f"Error initializing ArangoDB graph: {arango_error}")


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
@limiter.limit("10 per minute")
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