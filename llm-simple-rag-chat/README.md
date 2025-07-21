# LLM Simple RAG Chat

A RAG (Retrieval-Augmented Generation) chat tool that allows you to index documents and ask questions about them. It uses two models:
- A reasoning model for generating responses (default: models/gemini-2.0-flash)
- An embedding model for document indexing (default: models/embedding-001)

The tool supports both Google Generative AI embeddings and HuggingFace embeddings, and includes answer evaluation capabilities via MLflow.

## Features

- Interactive and automated question modes
- Answer evaluation with MLflow metrics
- Document indexing and retrieval
- Support for both Google and HuggingFace embeddings
- Model validation and listing

## Command Line Arguments

```bash
python ./llm-simple-rag-chat.py [options]
```

Generic Options:
- `-v, --verbose`: Enable verbose mode (use -vv for max verbosity)
- `-l, --logfile`: Specify log filename

Model Options:
- `--reasoning-model`: Gemini model for reasoning/chat (default: models/gemini-2.0-flash)
- `--embedding-model`: Gemini model for embeddings (default: models/embedding-001)
- `--list-models`: List available Google models and exit (useful for validating API token and selecting models)

Document Options:
- `--documents-folder`: Path to the documents folder (default: ./documents)

Evaluation Options:
- `--analyze-results`: Analyze existing evaluation results and print summary statistics
- `--results-folder`: Path to the folder containing evaluation results (default: .results)

Mode Options:
- `--mode`: Mode of operation (choices: interactive, auto, default: interactive)
- `--questions-file`: Path to the questions JSON file (default: questions.json)
- `--cache-dir`: Directory to store cached artifacts and data (default: .cache)

## Installation

1. Create a separate virtual environment for llm-simple-rag-chat:
   ```bash
   python -m venv venv-rag
   source venv-rag/bin/activate  # On Windows: venv-rag\Scripts\activate
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## API Key Setup for Gemini

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

## Usage Examples

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

List available Google models:
```bash
python ./llm-simple-rag-chat.py --list-models
```

## Answer Evaluation

The tool provides answer evaluation in both interactive and auto modes using MLflow metrics. Evaluation results include:
- Exact match score
- Readability metrics (Flesch-Kincaid grade level, ARI grade level)
- Token count

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

## Questions File Format

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
