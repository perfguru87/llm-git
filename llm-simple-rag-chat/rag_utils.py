import os
import json
import hashlib
import operator
import httpx
import numpy as np
from torch import nn
from typing import List, Optional
from langchain_core.documents import Document
from pydantic import Field, PrivateAttr, SecretStr
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain.retrievers.document_compressors.base import BaseDocumentCompressor
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_core.utils.utils import secret_from_env
from langchain_core.embeddings import Embeddings
from langchain_core.runnables import chain, Runnable
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy

def sigmoid(x):
    """Sigmoid function to normalize scores."""
    return 1 / (1 + np.exp(-x))

class ScoredTEICrossEncoderReranker(BaseDocumentCompressor, Runnable):
    name: str = Field(default="huggingface-api-reranker")  # Required by parent
    score_threshold: float | None = Field(default=None)
    normalize_scores: bool = Field(default=True)

    _model_url: str = PrivateAttr()
    _headers: dict = PrivateAttr()
    _top_n: int = PrivateAttr()

    api_token: Optional[SecretStr] = Field(
        alias="api_key", default_factory=secret_from_env("HUGGINGFACE_TEI_API_TOKEN", default=None)
    )

    def __init__(self, model_url: str, top_n: int = 5, api_token: str | None = None, normalize_scores: bool = True, score_threshold: float | None = None):
        super().__init__()
        # TODO: Load tokenizer to split documents into supported length?
        self._model_url = model_url
        self._headers = {"Authorization": f"Bearer {api_token}"}
        self._top_n = top_n
        self.score_threshold = score_threshold
        self.normalize_scores = normalize_scores

    def compress_documents(self, documents: List[Document], query: str, callbacks = None) -> List[Document]:
        return self.invoke(documents, query)

    def invoke(self, documents: List[Document], query: str, **kwargs) -> List[Document]:
        scores = []

        normalize_fn = sigmoid if self.normalize_scores else lambda x: x

        payload = {
            "query": query,
            "documents": [doc.page_content for doc in documents],
            "top_n": self._top_n,
        }
        response = httpx.post(self._model_url, headers=self._headers, json=payload)
        if response.status_code == 200:
            results = response.json()['results']
            for doc, result in zip(documents, results):
                score = result['relevance_score']
                scores.append((doc, normalize_fn(score)))
        else:
            print(f"API error ({response.status_code}): {response.text}")
            return []

        result = sorted(scores, key=operator.itemgetter(1), reverse=True)
        out = []
        for doc, score in result[: self._top_n]:
            if self.score_threshold is None or score >= self.score_threshold:
                doc.metadata['reranker_score'] = float(score)
                out.append(doc)
        return out

class ScoredCrossEncoderReranker(CrossEncoderReranker):
    score_threshold: float | None = Field(default=None)

    def compress_documents(self, documents, query, callbacks = None):
        scores = self.model.score([(query, doc.page_content) for doc in documents])
        docs_with_scores = list(zip(documents, scores))
        result = sorted(docs_with_scores, key=operator.itemgetter(1), reverse=True)
        out = []
        for doc, score in result[: self.top_n]:
            if self.score_threshold is None or score >= self.score_threshold:
                doc.metadata['reranker_score'] = float(score.item())
                out.append(doc)
        return out

def get_cached_vector_store(collection_name: str, embedding_model: str, chunks: List[Document], embedding: Embeddings, cache_dir: str):
    vector_store_path = os.path.join(cache_dir, f"vector_store", embedding_model, collection_name)
    state_file_path = os.path.join(vector_store_path, "vector_state.json")

    # Create hash of chunks using hashlib
    chunks_data = [(chunk.page_content, str(chunk.metadata)) for chunk in chunks]
    chunks_str = str(chunks_data).encode('utf-8')
    chunks_hash = hashlib.sha256(chunks_str).hexdigest()

    # First check if state file exists and matches
    if os.path.exists(state_file_path):
        try:
            with open(state_file_path, 'r') as f:
                state = json.load(f)
            if state.get('embedding_model') == embedding_model and state.get('chunks_hash') == chunks_hash:
                # Try to load vector store
                vector_store = FAISS.load_local(
                    vector_store_path,
                    embedding,
                    allow_dangerous_deserialization=True,
                    distance_strategy=DistanceStrategy.COSINE,
                    relevance_score_fn=lambda distance: (2 - distance) / 2
                )
                print("Loaded existing vector store from disk")
                return vector_store
        except Exception as e:
            print(f"Error loading cached vector store: {e}")

    # If we got here, either state file doesn't exist or state doesn't match
    print("State mismatch detected, creating new vector store")

    # Create new vector store and persist it
    # TODO: Support for other vector storages
    vector_store = FAISS.from_documents(
        chunks,
        embedding,
        distance_strategy=DistanceStrategy.COSINE,
        # NOTE: FAISS always returns distances in the range [0, 2] (0 similar, 2 dissimilar,
        # so we normalize it to [1, 0] (1 similar, 0 dissimilar)
        # TODO: Not sure if this formula is correct
        relevance_score_fn=lambda distance: (2 - distance) / 2
    )
    vector_store.save_local(vector_store_path)
    print("Vector store created and persisted to disk.")

    # Save state file
    state = {
        'embedding_model': embedding_model,
        'chunks_hash': chunks_hash
    }
    with open(state_file_path, 'w') as f:
        json.dump(state, f)

    return vector_store


def create_document_reranker(
    provider: str | None,
    model: str | None,
    url: str | None,
    top_n: int,
    normalize_scores: bool,
    score_threshold: float | None,
) -> BaseDocumentCompressor | None:
    if not provider:
        return None

    if provider == 'huggingface':
        print('Using HuggingFace document reranker:', model, 'with top_n:', top_n)
        return ScoredCrossEncoderReranker(
            model=HuggingFaceCrossEncoder(
                model_name=model,
                model_kwargs={'activation_fn': nn.Sigmoid() if normalize_scores else None}
            ),
            top_n=top_n,
            score_threshold=score_threshold
        )
    elif provider == 'huggingface-tei':
        if not url:
            raise Exception("External document reranker URL.")
        print('Using HuggingFace TEI document reranker:', url, 'with top_n:', top_n)
        return ScoredTEICrossEncoderReranker(
            model_url=url,
            top_n=top_n,
            score_threshold=score_threshold,
            normalize_scores=normalize_scores,
        )

    raise ValueError(f"Unsupported document reranker provider: {provider}")

def build_rag_system(
    llm,
    embedding: Embeddings,
    embedding_top_k: int,
    embedding_score_threshold: float | None,
    use_bm25_reranker: bool,
    bm25_weight: float,
    bm25_top_k: int,
    reranker: BaseDocumentCompressor | None,
    chunks: List[Document],
    cache_dir: str,
    collection_name: str,
):
    print(f"Initializing embedding with model: {embedding.model}")

    # Get or create vector store
    vector_store = get_cached_vector_store(collection_name, embedding.model, chunks, embedding, cache_dir)

    @chain
    def vector_retriever(query: str):
        kwargs = {}
        if embedding_score_threshold is not None:
            kwargs["score_threshold"] = embedding_score_threshold
        docs, scores = zip(*vector_store.similarity_search_with_relevance_scores(query, embedding_top_k, **kwargs))
        for doc, score in zip(docs, scores):
            doc.metadata["similarity_score"] = float(score)
        return docs

    retrievers = [vector_retriever]
    # Default weight for vector retriever
    weights = [1]
    if use_bm25_reranker:
        print('Using BM25 retriever with top_k:', bm25_top_k)
        retrievers += [BM25Retriever.from_documents(chunks, search_kwargs={"k": bm25_top_k})]
        # Adjust weight of vector retriever
        weights[0] -= bm25_weight
        # Add BM25 weight
        weights += [bm25_weight]

    # Create ensembled retriever
    base_retriever = EnsembleRetriever(
        retrievers=retrievers,
        weights=weights
    )

    if reranker is not None:
        retriever = ContextualCompressionRetriever(
            base_compressor=reranker, base_retriever=base_retriever
        )
    else:
        retriever = base_retriever

    # Define custom prompt
    # TODO: Extend prompt with specific guidelines (abbreviations, base concepts, etc.)
    template = """Use the following pieces of context to answer the user's question.
If the context does not provide sufficient or relevant information, just say that you don't know.
Base your answer only on the provided context. Don't try to make up an answer.

Context: {context}

Question: {question}

Answer:"""
    RAG_PROMPT = PromptTemplate(template=template, input_variables=["context", "question"])

    # Build RAG chain
    return RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": RAG_PROMPT}
    )
