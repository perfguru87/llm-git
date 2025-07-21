# LLM-Git Tools

A collection of Git-related tools enhanced with Large Language Models (LLMs) to improve developer workflows.

## Overview

This repository contains tools that leverage LLMs to enhance Git-related workflows:

- **llm-git-commit**: Generates meaningful commit messages by analyzing your git diff
- **llm-go-cov-prompt**: Analyzes Go code coverage and helps identify areas that need unit tests
- **llm-simple-rag-chat**: A RAG (Retrieval-Augmented Generation) chat tool for document indexing and Q&A (see [llm-simple-rag-chat/README.md](llm-simple-rag-chat/README.md))

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

A RAG (Retrieval-Augmented Generation) chat tool that allows you to index documents and ask questions about them.

For detailed information, installation instructions, and usage examples, see the [dedicated README file](llm-simple-rag-chat/README.md).

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

### LLM Simple RAG Chat

See the [dedicated README file](llm-simple-rag-chat/README.md) for detailed information on how this tool works.

## Configuration

Both tools will automatically discover available LLM endpoints and models. By default, they check:

- LM Studio: http://127.0.0.1:1234 and http://localhost:1234
- Ollama: http://127.0.0.1:11434 and http://localhost:11434

You can specify a custom endpoint with the `--api-url` option.

## License

[Apache 2.0 License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.