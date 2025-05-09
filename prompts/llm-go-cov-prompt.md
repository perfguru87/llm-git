This prompt duplicates the logic of the `llm-go-cov-prompt.py` tool. It is intended for use cases where the same coverage analysis and annotation should be performed via prompt, rather than via the Python script.

Read the content from llm-go-cov-reqs.md, use files in <path/to/source/folder> as input and process all the instructions.

**Example query:**
```
Read the content from llm-go-cov-reqs.md, use files in <path/to/source/folder> as input and process all the instructions.
```

Replace `<path/to/source/folder>` with the directory containing your Go source files.
