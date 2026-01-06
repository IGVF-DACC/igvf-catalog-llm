# Shared constants for the IGVF Catalog LLM application
import os

# Default limit for AQL query results
DEFAULT_LIMIT = 100

# Database and API configuration
BACKEND_URL = os.environ.get('BACKEND_URL', 'https://db-dev.catalog.igvf.org/')
DB_NAME = 'igvf'
OPENAI_MODEL = 'gpt-4.1'
