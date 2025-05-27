# IGVF Catalog LLM

## Overview

IGVF Catalog LLM is a Flask-based web application that leverages OpenAI's GPT models and LangChain to translate natural language questions into ArangoDB AQL queries, enabling advanced querying of the IGVF Catalog knowledge graph. The project also includes AWS CDK infrastructure-as-code for cloud deployment.

## Features

- Natural language to AQL translation using OpenAI GPT-4o and LangChain
- Query ArangoDB for genomics and biomedical data
- Example-driven prompt engineering for accurate AQL generation
- Docker and docker-compose support for easy deployment
- AWS CDK scripts for cloud infrastructure

## Directory Structure

```
.
├── igvf-catalog-llm/         # Flask app and core logic
│   ├── app.py                # Main Flask application
│   ├── requirements.txt      # Python dependencies
│   ├── aql_examples.py       # Example AQL queries
│   ├── select_collections.py # Collection selection logic
│   └── prompt_template.py    # Prompt template for LLM
├── cdk/                     # AWS CDK infrastructure code
├── docker/                  # Docker-related files
├── docker-compose.yaml      # Docker Compose setup
└── README.md                # Project documentation
```

## Requirements

- Python 3.9+
- Catalog ArangoDB instance (cloud or local)
- OpenAI API key
- Docker (optional, for containerized deployment)

## Setup

### 1. Set environment variables

Create a `.env` file for following variables:

- `CATALOG_USERNAME` (ArangoDB username)
- `CATALOG_PASSWORD` (ArangoDB password)
- `OPENAI_API_KEY` (OpenAI API key)

### 2. Run with Docker Compose

```sh
docker-compose up --build
```

The app will be available at [http://localhost:5000](http://localhost:5000)

## API Endpoints

### Health Check

```bash
GET /health
```

Returns the status of the ArangoDB connection and LLM initialization.

### Query Endpoint

```bash
POST /query
Content-Type: application/json
{
  "password": "<CATALOG_PASSWORD>",
  "query": "Tell me about gene SAMD11"
}
```

Returns a JSON response with the AQL query, results, and metadata.

## Infrastructure (AWS CDK)

- The `cdk/` directory contains AWS CDK scripts for deploying the app and related resources (e.g., Fargate, Load Balancer, Route 53).
- See `cdk/README.md` for CDK usage and commands.
