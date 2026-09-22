import os
import re

BACKEND_URL = os.environ.get('BACKEND_URL', 'https://db-dev.catalog.igvf.org/')
DB_NAME = 'igvf'
OPENAI_MODEL = 'gpt-4.1'

QUERY_AQL_LIMIT = 5
MAX_AQL_LIMIT = 100
MAX_AQL_GENERATION_ATTEMPTS = 5

AQL_COUNT_AGGREGATION_PATTERN = re.compile(
    r'\bRETURN\s+(LENGTH|COUNT|SUM|AVG|MIN|MAX)\s*\(', re.IGNORECASE)
AQL_LIMIT_PATTERN = re.compile(
    r'\bLIMIT\s+\d+(?:\s*,\s*\d+)?\b', re.IGNORECASE)
AQL_CODE_BLOCK_PATTERN = re.compile(r'```(?i:aql)?(.*?)```', re.DOTALL)
AQL_WRITE_PATTERN = re.compile(
    r'\b(INSERT|UPDATE|REPLACE|REMOVE|UPSERT)\b', re.IGNORECASE)
