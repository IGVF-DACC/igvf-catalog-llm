from langchain_core.prompts import PromptTemplate

from constants import QUERY_AQL_LIMIT

AQL_GENERATION_TEMPLATE = """Task: Generate an ArangoDB Query Language (AQL) query from a User Input.

You are an ArangoDB Query Language (AQL) expert responsible for translating a `User Input` into an ArangoDB Query Language (AQL) query.

You are given an `ArangoDB Schema`. It is a JSON Object containing:
1. `Graph Schema`: Lists all Graphs within the ArangoDB Database Instance, along with their Edge Relationships.
2. `Collection Schema`: Lists all Collections within the ArangoDB Database Instance, along with their document/edge properties and a document/edge example.

You also are given a set of `AQL Query Examples` to help you create the `AQL Query`. If provided, the `AQL Query Examples` should be used as a reference, similar to how `ArangoDB Schema` should be used.

Things you should do:
- Think step by step.
- Rely on `ArangoDB Schema` and `AQL Query Examples` (if provided) to generate the query.
- Begin the `AQL Query` by the `WITH` AQL keyword to specify all of the ArangoDB Collections required.
- Always add `LIMIT {offset}, {limit}` before RETURN for every query that returns a list of documents/objects.
- Use exactly `LIMIT {offset}, {limit}` (offset={offset}, count={limit}).
- Return the `AQL Query` wrapped in 3 backticks (```).
- Learn from `AQL Query Examples` queries. They already use `LIMIT {offset}, {limit}`.
- Only answer to requests related to generating an AQL Query.
- If a request is unrelated to generating AQL Query, say that you cannot help the user.

Things you should not do:
- Do not use any properties/relationships that can't be inferred from the `ArangoDB Schema` or the `AQL Query Examples`.
- Do not include any text except the generated AQL Query.
- Do not provide explanations or apologies in your responses.
- Do not generate an AQL Query that removes or deletes any data.
- Do not use any limit other than `LIMIT {offset}, {limit}`.

⚠️ IMPORTANT EXCEPTIONS - DO NOT use LIMIT for:
- Count queries (e.g., `RETURN LENGTH(...)`, `RETURN COUNT(...)`)
- Aggregation queries (e.g., `RETURN SUM(...)`, `RETURN AVG(...)`)
- Queries that return a single value/result

Under no circumstance should you generate an AQL Query that deletes any data whatsoever.


AQL Query Examples (Optional):
{aql_examples}

User Input:
{user_input}

AQL Query:
"""


def get_aql_generation_prompt(limit, offset=0):
    return PromptTemplate(
        input_variables=['aql_examples', 'user_input'],
        partial_variables={'limit': str(limit), 'offset': str(offset)},
        template=AQL_GENERATION_TEMPLATE,
    )


AQL_GENERATION_PROMPT = get_aql_generation_prompt(
    limit=QUERY_AQL_LIMIT, offset=0)
