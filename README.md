# LLM-Git Tools

A collection of Git-related tools enhanced with Large Language Models (LLMs) to improve developer workflows.

## Overview

This repository contains tools that leverage LLMs to enhance Git-related workflows:

- **llm-git-commit**: Generates meaningful commit messages by analyzing your git diff
- **llm-go-cov-prompt**: Analyzes Go code coverage and helps identify areas that need unit tests

These tools work with local LLM servers like LM Studio and Ollama, or can be configured to use cloud-based APIs like OpenAI.

## Prompts Folder

The `prompts` directory contains reusable prompt templates for LLM-powered tools in this repository. These prompts can be used directly with LLMs or as part of automated workflows, and may duplicate the logic of the corresponding Python tools for prompt-based usage.

## Requirements

- Python 3.6+
- Git
- Local LLM server (recommended):
  - [LM Studio](https://lmstudio.ai/) (default port: 1234)
  - [Ollama](https://ollama.ai/) (default port: 11434)
- Or API keys for cloud services:
  - OpenAI API key (set as `OPENAI_API_KEY` environment variable)
  - Anthropic API key (set as `ANTHROPIC_API_KEY` environment variable)

## Installation

```bash
# Clone the repository
git clone git@github.com:perfguru87/llm-git.git
cd llm-git

# Optional: Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### LLM Git Commit

Generates meaningful commit messages by analyzing your git diff:

```bash
python llm-git-commit.py [options]
```

Options:
- `--temperature`: LLM temperature parameter (default: 0.5)
- `--max-tokens`: Maximum tokens for LLM response (default: 8192)
- `--api-url`: Custom API endpoint URL
- `-m, --model`: LLM model to use (e.g., gpt-4, gpt-3.5-turbo, qwen)
- `-v, --verbose`: Increase verbosity level (-v for INFO, -vv for DEBUG)
- `-q, --quiet`: Quiet mode - don't show patch

### LLM Go Coverage Prompt

Analyzes Go code coverage and helps identify areas that need unit tests:

```bash
python llm-go-cov-prompt.py [options] [files/directories]
```

Options:
- `-c, --coverage-out-file`: Path to the coverage output file (default: coverage.out)
- `-t, --threshold`: Skip files with coverage percentage above this threshold
- `-v, --verbose`: Increase verbosity level (-v for INFO, -vv for DEBUG)
- `-q, --quiet`: Quiet mode

### LLM Simple RAG Chat

A RAG (Retrieval-Augmented Generation) chat tool that allows you to index documents and ask questions about them. It uses two models:

- A chat model for generating responses (default: models/gemini-2.0-flash)
- An embedding model for document indexing (default: models/embedding-001)

The tool supports both Google Generative AI embeddings and HuggingFace embeddings, and includes answer evaluation capabilities via MLflow.

#### Features

- Interactive and automated question modes
- Answer evaluation with MLflow metrics
- Document indexing and retrieval
- Support for both Google and HuggingFace embeddings
- Model validation and listing

#### Command Line Arguments


```bash
python ./llm-simple-rag-chat.py [options]
```

**Generic Options:**

- `-v, --verbose`                 Enable verbose mode (use -vv for max verbosity)
- `-l, --logfile`                 Specify log filename

**Model Options:**

- `--chat-model-provider`         Chat model provider (e.g., google, huggingface, openai, etc.; default: google)
- `--chat-model-url`              Base URL for the chat model (if using an external API; default: None)
- `--chat-model-name`             Chat model name (default: models/gemini-2.0-flash)
- `--embedding-model-provider`    Embedding model provider (e.g., google, huggingface, etc.; default: google)
- `--embedding-model-url`         Base URL for the embedding model (if using an external API; default: None)
- `--embedding-model-name`        Embedding model name (default: models/embedding-001)
- `--list-models`                 List available Google models and exit (useful for validating API token and selecting models)
- `--temperature`                 Model temperature for controlling randomness in responses (default: 0.1)
- `--n-tokens`                    Maximum number of tokens for model responses (default: 1024)
- `--top-p`                       Top-p sampling parameter for controlling diversity of responses (default: 0.95)
- `--top-k`                       Top-k sampling parameter for controlling diversity of responses (default: 20)

**Document Options:**

- `-d, --documents-folder`        Path to the documents folder (default: ./documents)
- `--documents-collection-name`   Name of the vector index collection (default: default)
- `--documents-chunk-size`        Size of the split document chunk in tokens (default: 800)
- `--documents-chunk-overlap-size` Size of the chunk overlap in tokens (default: 80)

**Evaluation Options:**

- `--analyze-results`             Analyze existing evaluation results and print summary statistics
- `--results-folder`              Path to the folder containing evaluation results (default: .results)
- `--llm-as-a-judge`              Use LLM-based metrics for answer evaluation

**Mode Options:**

- `--mode`                        Mode of operation: interactive (manual chat) or auto (automated questions) (default: interactive)
- `--questions-file`              Path to the questions JSON file (default: questions.json)
- `--cache-dir`                   Directory to store cached artifacts and data (default: .cache)

**General RAG Options:**

- `--embeddings-top-k`            Number of vector search candidates to retrieve (default: 75)
- `--embeddings-score-threshold`  Filter vector search results by similarity score threshold (default: None)

**Hybrid RAG Options:**

- `--use-bm25-reranker`           Enable BM25 (keyword-based) reranking (default: False)
- `--bm25-top-k`                  Number of BM25 candidates to retrieve (default: 50)
- `--bm25-weight`                 Weight of BM25 candidates (default: 0.5)
- `--document-reranker-provider`  Enable document reranking with cross-encoder model (default: None)
- `--document-reranker-model`     Name of the document reranker model from HuggingFace (default: cross-encoder/ms-marco-MiniLM-L6-v2)
- `--document-reranker-url`       URL of the external reranker model (default: None)
- `--document-reranker-api-token` API token for the external reranker model (default: None)
- `--document-reranker-top-n`     Number of documents that reranker model should keep (default: 10)
- `--document-reranker-normalize-scores/--no-document-reranker-normalize-scores` Apply Sigmoid normalization to scores (default: True)
- `--document-reranker-score-threshold` Filter reranker results by relevance score threshold (default: None)

#### Installation

1. Create a separate virtual environment for llm-simple-rag-chat:
   ```bash
   python -m venv venv-rag
   source venv-rag/bin/activate  # On Windows: venv-rag\Scripts\activate
   ```

2. Install the required dependencies:
   ```bash
   pip install -r llm-simple-rag-chat-requirements.txt
   ```

#### API Key Setup for Gemini

To use the Google Generative AI features:

1. Copy the `.env.example` file to create your `.env` file:
   ```bash
   cp .env.example .env
   ```

2. Obtain a free tier Gemini API key:
   1. Go to Google AI Studio: Visit https://aistudio.google.com/.
   2. Sign in with your Google account.
   3. Click "Get API key" (usually in the top left or center of the page).
   4. Agree to the terms of service.
   5. Click "Create API key" (you can choose to create in a new or existing project).
   6. Copy your generated API key and store it in your `.env` file as `GEMINI_API_KEY`.

Note: You may encounter 400 errors due to rate limiting and quotas in Google's services. In such cases, it's recommended to wait a couple of minutes and try again.

#### Usage Examples

Basic usage:
```bash
python ./llm-simple-rag-chat.py --documents-folder /path/to/documents
```

Interactive mode (default):
```bash
python ./llm-simple-rag-chat.py --documents-folder /path/to/docs --mode interactive
```

Auto mode with custom questions file:
```bash
python ./llm-simple-rag-chat.py --documents-folder /path/to/docs --mode auto --questions-file custom_questions.json
```

Using HuggingFace embeddings:
```bash
python ./llm-simple-rag-chat.py --documents-folder /path/to/docs --embedding-model all-MiniLM-L6-v2
```

Using LLM-as-a-judge with custom Ollama configuration:
```bash
python ./llm-simple-rag-chat.py --documents-folder /path/to/docs --mode auto --llm-as-a-judge --ollama-address http://localhost:11434 --ollama-model mistral:7b
```

Note: The LLM-as-a-judge feature is optimized for batch evaluation in auto mode, as it leverages MLflow's evaluation pipeline to process multiple questions efficiently. While it can be used in interactive mode, auto mode is recommended for comprehensive evaluation of answer quality across multiple questions.

List available Google models:
```bash
python ./llm-simple-rag-chat.py --list-models
```

#### Answer Evaluation

The tool provides answer evaluation in both interactive and auto modes using MLflow metrics. Evaluation results include:
- Exact match score
- Readability metrics (Flesch-Kincaid grade level, ARI grade level)
- Token count

When using `--llm-as-a-judge` option, the tool leverages Ollama models to perform additional LLM-based evaluations:
- Answer similarity: How similar the response is to the reference answer
- Answer correctness: How factually correct the response is
- Answer relevance: How relevant the response is to the question
- Relevance: How relevant the source documents are (if provided)
- Faithfulness: How faithful the answer is to the source documents (if provided)

In interactive mode, you can provide reference answers after each question, and the tool will evaluate the response immediately. In auto mode, the tool automatically evaluates answers against pre-defined reference answers from the questions file.

All evaluation results are stored in the `.results` folder, organized by timestamp and model. Each result file contains detailed metrics for every question, including:
- Per-category statistics
- Score distributions
- Readability metrics
- Token usage

You can analyze these results later using the `--analyze-results` option to get average scores per result file and per question category. For example:

```bash
# Analyze all evaluation results
python ./llm-simple-rag-chat.py --analyze-results

# Analyze results from a specific folder
python ./llm-simple-rag-chat.py --analyze-results --results-folder /path/to/results
```

#### Questions File Format

The questions file (default: `questions.json`) is a JSON file that organizes questions into categories. Each category can contain multiple questions. The structure is as follows:

```json
{
    "categories": {
        "CategoryName": {
            "questions": [
                {
                    "question": "What is the primary purpose of Data Transfer Services?",
                    "reference_answer": "DTS is designed to facilitate secure and efficient data movement between systems. It provides reliable transfer mechanisms with built-in error handling and monitoring capabilities.",
                    "weight": 0.9
                }
            ]
        }
    }
}
```

Required fields:
- `question`: The question to be asked (string)
- `reference_answer`: The correct answer for evaluation (string)
- `weight`: A numerical weight for the question (float, default: 1.0)

## How It Works

### LLM Git Commit

1. Analyzes both staged and unstaged changes in your git repository
2. Sends the diff to an LLM with a prompt to generate a meaningful commit message
3. Shows you the proposed commit message and asks for confirmation
4. If confirmed, creates the commit with the generated message

### LLM Go Coverage Prompt

1. Parses a Go coverage output file (typically generated with `go test -coverprofile=coverage.out`)
2. Identifies uncovered code sections
3. Displays the uncovered code with annotations to help you write appropriate unit tests

## Configuration

Both tools will automatically discover available LLM endpoints and models. By default, they check:

- LM Studio: http://127.0.0.1:1234 and http://localhost:1234
- Ollama: http://127.0.0.1:11434 and http://localhost:11434

You can specify a custom endpoint with the `--api-url` option.

## License

[Apache 2.0 License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
