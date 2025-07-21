import os
import json
import pickle
from typing import Callable, List, Tuple
from datetime import datetime
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter, MarkdownTextSplitter
from langchain.schema import Document

def get_folder_mtimes(folder_path):
    mtimes = {}
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                mtimes[file_path] = os.path.getmtime(file_path)
            except OSError:
                # Handle cases where file might be inaccessible or disappear
                pass
    return mtimes

def _save_mtimes(cache_file_path, current_mtimes):
    """Helper function to save modification times to cache file"""
    try:
        with open(cache_file_path, 'w') as f:
            json.dump(current_mtimes, f, indent=2)
        print(f"Successfully saved modification times to: {cache_file_path}")
    except Exception as e:
        print(f"Error saving modification times: {e}")

def check_folder_for_changes_mtime(folder_path, cache_file="mtime_cache.json", cache_dir=".cache"):
    current_mtimes = get_folder_mtimes(folder_path)

    # Create cache directory if it doesn't exist
    os.makedirs(cache_dir, exist_ok=True)
    cache_file_path = os.path.join(cache_dir, cache_file)

    if not os.path.exists(cache_file_path):
        print(f"Cache file '{cache_file}' not found. Creating new cache file.")
        # Save current modification times to new cache file
        try:
            # First ensure we have valid modification times
            if not current_mtimes:
                print("Warning: No modification times found in current folder")
                return True, current_mtimes

            _save_mtimes(cache_file_path, current_mtimes)
            return True, current_mtimes
        except Exception as e:
            print(f"Error creating new cache file: {e}")
            return True, current_mtimes

    try:
        with open(cache_file_path, 'r') as f:
            content = f.read()
            if not content.strip():  # Check if file is empty
                print(f"Empty cache file found. Assuming changes detected.")
                _save_mtimes(cache_file_path, current_mtimes)
                return True, current_mtimes
            previous_mtimes = json.loads(content)
    except json.JSONDecodeError:
        print(f"Error decoding cache file '{cache_file}'. Assuming changes detected.")
        _save_mtimes(cache_file_path, current_mtimes)
        return True, current_mtimes
    except Exception as e:
        print(f"Error reading cache file '{cache_file}': {e}")
        _save_mtimes(cache_file_path, current_mtimes)
        return True, current_mtimes

    # Check for added, removed, or modified files
    changed = False

    # Check for modified or removed files
    for path, prev_mtime in previous_mtimes.items():
        if path not in current_mtimes:
            print(f"Removed: {path}")
            changed = True
        elif current_mtimes[path] != prev_mtime:
            print(f"Modified: {path} (Prev: {datetime.fromtimestamp(prev_mtime)}, Current: {datetime.fromtimestamp(current_mtimes[path])})")
            changed = True

    # Check for added files
    for path in current_mtimes:
        if path not in previous_mtimes:
            print(f"Added: {path}")
            changed = True

    # Save current modification times to cache
    _save_mtimes(cache_file_path, current_mtimes)

    return changed, current_mtimes


def load_and_cache_chunks(
    documents_folder: str,
    chunk_size: int,
    chunk_overlap_size: int,
    llm_tokenizer_fn: Callable,
    cache_dir: str
) -> Tuple[List[Document], bool]:
    """
    Load and cache document chunks with modification time checking.

    Args:
        documents_folder (str): Path to the documents folder
        cache_dir (str): Directory to store cached chunks and metadata

    Returns:
        tuple: (chunks, changed)
            chunks: List of document chunks
            changed: Boolean indicating if documents were modified
    """
    # Check for document changes
    changed, current_mtimes = check_folder_for_changes_mtime(
        documents_folder,
        cache_file="mtime_cache.json",
        cache_dir=cache_dir
    )

    # Try to load cached chunks if no changes detected
    if not changed:
        chunks_cache_path = os.path.join(cache_dir, "document_chunks.pkl")
        if os.path.exists(chunks_cache_path):
            try:
                with open(chunks_cache_path, 'rb') as f:
                    return pickle.load(f), False
            except Exception as e:
                print(f"Error loading cached chunks: {e}")

    # Load and process documents
    chunks = load_and_split_documents(documents_folder, chunk_size, chunk_overlap_size, llm_tokenizer_fn)

    # Save chunks to cache
    chunks_cache_path = os.path.join(cache_dir, "document_chunks.pkl")
    try:
        with open(chunks_cache_path, 'wb') as f:
            pickle.dump(chunks, f, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception as e:
        print(f"Error saving chunks to cache: {e}")

    return chunks, True

def load_and_split_documents(
    document_folder: str,
    chunk_size: int,
    chunk_overlap: int,
    llm_num_tokens_fn: Callable,
) -> List[Document]:
    print(f"Starting to load documents from: {document_folder}")
    md_documents:  List[Document] = []
    pdf_documents: List[Document] = []
    txt_documents: List[Document] = []

    # Use os.walk to traverse through the main folder and all its subfolders
    for dirpath, dirnames, filenames in os.walk(document_folder):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)

            # Determine the correct loader based on file extension
            if filename.endswith(".pdf"):
                try:
                    loader = PyMuPDFLoader(file_path)
                    loaded_docs = loader.load()
                    pdf_documents.extend(loaded_docs)
                    print(f"Loaded PDF: {file_path}")
                except Exception as e:
                    print(f"Error loading PDF {file_path}: {e}")
            elif filename.endswith(".txt"):
                try:
                    loader = TextLoader(file_path, encoding='utf-8')  # Specify encoding for text files
                    loaded_docs = loader.load()
                    txt_documents.extend(loaded_docs)
                    print(f"Loaded TXT: {file_path}")
                except Exception as e:
                    print(f"Error loading TXT {file_path}: {e}")
            elif filename.endswith(".md") or filename.endswith(".markdown"):
                try:
                    loader = TextLoader(file_path, encoding='utf-8')  # Specify encoding for text files
                    loaded_docs = loader.load()
                    md_documents.extend(loaded_docs)
                    print(f"Loaded Markdown: {file_path}")
                except Exception as e:
                    print(f"Error loading Markdown {file_path}: {e}")
            # Add more `elif` conditions here for other document types (e.g., .docx, .html)
            # elif filename.endswith(".docx"):
            #     try:
            #         from langchain_community.document_loaders import UnstructuredWordDocumentLoader
            #         loader = UnstructuredWordDocumentLoader(file_path)
            #         loaded_docs = loader.load()
            #         if loaded_docs is not None:
            #             documents.extend(loaded_docs)
            #         print(f"Loaded DOCX: {file_path}")
            #     except Exception as e:
            #         print(f"Error loading DOCX {file_path}: {e}")
            else:
                print(f"Skipping unsupported file type: {file_path}")

    print(f"\nFinished loading. Total documents loaded: {len(md_documents) + len(pdf_documents) + len(txt_documents)}")

    # TODO: Need to keep line and column numbers for text files
    md_chunks = MarkdownTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=llm_num_tokens_fn,
    ).split_documents(md_documents)
    pdf_chunks = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=llm_num_tokens_fn,
    ).split_documents(pdf_documents)
    txt_chunks = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=llm_num_tokens_fn,
    ).split_documents(txt_documents)
    return md_chunks + pdf_chunks + txt_chunks
