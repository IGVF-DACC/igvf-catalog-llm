import os
import re
from pathlib import Path

BACKEND_URL = os.environ.get('BACKEND_URL', 'https://db-dev.catalog.igvf.org/')
DB_NAME = 'igvf'
OPENAI_MODEL = 'gpt-4.1'

QUERY_AQL_LIMIT = 5
MAX_AQL_LIMIT = 100
MAX_AQL_GENERATION_ATTEMPTS = 5

# Repo root is the parent of the igvf-catalog-llm package directory.
# Commit both curated_edge_schema.{dev,prod}.json; CDK/local set CURATED_EDGE_SCHEMA_PATH
# like BACKEND_URL (default: .dev.json for local / db-dev).
REPO_ROOT = Path(__file__).resolve().parent.parent
CURATED_EDGE_SCHEMA_DEV_PATH = REPO_ROOT / 'curated_edge_schema.dev.json'
CURATED_EDGE_SCHEMA_PROD_PATH = REPO_ROOT / 'curated_edge_schema.prod.json'
CURATED_EDGE_SCHEMA_PATH = Path(
    os.environ.get(
        'CURATED_EDGE_SCHEMA_PATH',
        str(CURATED_EDGE_SCHEMA_DEV_PATH),
    )
)

AQL_COUNT_AGGREGATION_PATTERN = re.compile(
    r'\bRETURN\s+(LENGTH|COUNT|SUM|AVG|MIN|MAX)\s*\(', re.IGNORECASE)
AQL_LIMIT_PATTERN = re.compile(
    r'\bLIMIT\s+\d+(?:\s*,\s*\d+)?\b', re.IGNORECASE)
AQL_CODE_BLOCK_PATTERN = re.compile(r'```(?i:aql)?(.*?)```', re.DOTALL)
AQL_WRITE_PATTERN = re.compile(
    r'\b(INSERT|UPDATE|REPLACE|REMOVE|UPSERT)\b', re.IGNORECASE)
