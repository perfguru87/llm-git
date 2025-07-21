import google.generativeai as genai
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings


def list_models():
    print("\nAvailable Google models:")
    print("\nModels with generateContent capability:")
    for model in genai.list_models():
        if "generateContent" in model.supported_generation_methods:
            print(f"  {model.name}")
    print("\nModels with embedContent capability:")
    for model in genai.list_models():
        if "embedContent" in model.supported_generation_methods:
            print(f"  {model.name}")


# Function to create embeddings based on model type
def create_embeddings(
    provider: str,
    model_name: str,
    model_url: str | None
):
    print(f"Initializing embeddings provider {provider} with model {model_name}")
    if provider == "google":
        return GoogleGenerativeAIEmbeddings(model=model_name)
    elif provider == "openai":
        if not model_url:
            raise ValueError("Model URL must be provided for OpenAI models.")
        return OpenAIEmbeddings(
            model=model_name,
            base_url=model_url,
            # chunk_size=512,
            # embedding_ctx_length=8191,
            # dimensions=1024,
        )
    elif provider == "openai-compat":
        if not model_url:
            raise ValueError("Model URL must be provided for OpenAI models.")
        return OpenAIEmbeddings(
            model=model_name,
            base_url=model_url,
            tiktoken_enabled=False, # HuggingFace tokenizer will be used instead of tiktoken based on the model name
        )
    elif provider == "huggingface":
        return HuggingFaceEmbeddings(
            model_name=model_name
        )
    raise ValueError(f"Unsupported embedding model provider: {provider}")


def create_llm(
    provider: str,
    model_name: str,
    model_url: str | None,
    temperature: float,
    n_tokens: int,
    top_p: float,
    top_k: int
):
    print(f"Initializing LLM provider {provider} with model {model_name}")

    # API Key is expected to be set in the environment variable
    if provider == "google":
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            max_tokens=n_tokens, # ChatGoogleGenerativeAI default is 64 tokens!
            top_p=top_p,
            top_k=top_k,
        )
    elif provider == "openai":
        if not model_url:
            raise ValueError("Model URL must be provided for OpenAI models.")
        llm = ChatOpenAI(
            model_name=model_name,
            base_url=model_url,
            temperature=temperature,
            max_tokens=n_tokens,
            top_p=top_p,
            # TODO: ChatOpenAI does not support top_k
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

    # Test the LLM
    print("Testing LLM...")
    response = llm.invoke("What is the capital of France? Give a short answer.")
    print(f"LLM Response: {response.content}")

    return llm
