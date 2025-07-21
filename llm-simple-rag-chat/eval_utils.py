import pandas as pd
import mlflow
import os
import requests
from typing import List, Dict
from mlflow.metrics.genai import answer_similarity, answer_correctness, answer_relevance, relevance, faithfulness

def configure_mlflow(model_url, mlflow_tracking_path=".mlflow", llm_as_a_judge=False):
    # TODO: Works only with OpenAI and OpenAI-compatible models
    # MLflow expects a URI. For local paths, prefix with 'file://'
    mlflow.set_tracking_uri(f"file://{os.path.abspath(mlflow_tracking_path)}")
    print(f"MLflow tracking data will be stored in: {mlflow_tracking_path}")
    print(f"MLflow tracking URI set to: {mlflow.get_tracking_uri()}")
    os.environ["MLFLOW_ENABLE_ARTIFACTS_PROGRESS_BAR"] = "false"

    # Configure MLflow environment variables for OpenAI adapter
    os.environ["OPENAI_API_BASE"] = model_url
    # TODO: OPENAI_API_KEY is already set by dotenv. Need to figure out how to handle case with other models.
    # os.environ["OPENAI_API_KEY"] = "test-key"  # Required by the OpenAI client library

    # Check LLM accessibility if llm_as_a_judge is True
    if llm_as_a_judge:
        try:
            response = requests.get(f"{model_url}/models")
            if response.status_code != 200:
                raise Exception("LLM instance is not accessible")
            print("LLM is accessible and ready for evaluation")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Cannot connect to LLM instance. Please ensure that OpenAI-compatible API is available on {model_url}")

def evaluate_answers(
    questions: List[Dict],
    model_name: str,
    model_kwargs: Dict | None = None,
    verbose: bool = True,
    llm_as_a_judge: bool = False,
) -> Dict:
    """
    Evaluate multiple question-answer pairs in batch.

    Args:
        questions: List of dictionaries containing:
            - question: The input question
            - answer: The model's answer to evaluate
            - reference_answer: The ground truth answer
            - weight: Optional weight for the evaluation (defaults to 1.0)
            - source_documents: Optional list of source documents
        verbose: Whether to print evaluation results
        llm_as_a_judge: Whether to use LLM for evaluation
        model_name: Name of the model to use for evaluation

    Returns:
        Dictionary containing evaluation metrics and results table
    """
    # Prepare evaluation data
    eval_data = pd.DataFrame({
        "inputs": [q['question'] for q in questions],
        "model_answer": [q['answer'] for q in questions],
        "ground_truth": [q['reference_answer'] for q in questions],
        "weights": [q.get('weight', 1.0) for q in questions]
    })

    # Add source documents if provided
    if any('source_documents' in q for q in questions):
        contexts = []
        for q in questions:
            if 'source_documents' in q and q['source_documents']:
                context = "\n".join([doc.page_content for doc in q['source_documents']])
            else:
                context = ""
            contexts.append(context)
        eval_data["context"] = contexts

    def create_metric_config(metric_func, model_kwargs = None):
        """Helper function to create metric configuration with common parameters."""
        return metric_func(
            model=f"openai:/{model_name}",
            parameters=model_kwargs,
            max_workers=1,
        )

    # Prepare metrics list based on llm_as_a_judge flag
    extra_metrics = []
    if llm_as_a_judge:
        extra_metrics.extend([
            create_metric_config(answer_similarity, model_kwargs),
            create_metric_config(answer_correctness, model_kwargs),
            create_metric_config(answer_relevance, model_kwargs),
        ])
        if 'context' in eval_data.columns:
            extra_metrics.extend([
                create_metric_config(relevance, model_kwargs),
                create_metric_config(faithfulness, model_kwargs),
            ])

    # Run evaluation
    with mlflow.start_run() as run:
        evaluator = mlflow.evaluate(
            data=eval_data,
            targets="ground_truth",
            extra_metrics=extra_metrics,
            predictions="model_answer",
            model_type="question-answering"
        )

        # Get evaluation results
        eval_table = evaluator.tables["eval_results_table"]
        metrics = evaluator.metrics

        if verbose:
            print("\nEvaluation Results:")
            print("-" * 50)
            print(f"Exact Match Score: {metrics.get('exact_match/v1', 0.0)}")
            if llm_as_a_judge:
                print(f"Answer Similarity Score Mean: {metrics.get('answer_similarity/v1/mean', 0.0)}")
                print(f"Answer Correctness Score Mean: {metrics.get('answer_correctness/v1/mean', 0.0)}")
                print(f"Answer Relevance Score Mean: {metrics.get('answer_relevance/v1/mean', 0.0)}")
                if 'context' in eval_data.columns:
                    print(f"Relevance Score Mean: {metrics.get('relevance/v1/mean', 0.0)}")
                    print(f"Faithfulness Score Mean: {metrics.get('faithfulness/v1/mean', 0.0)}")
            print(f"Flesch-Kincaid Grade Level: {metrics.get('flesch_kincaid_grade_level/v1/mean', 0.0):.2f}")
            print(f"ARI Grade Level: {metrics.get('ari_grade_level/v1/mean', 0.0):.2f}")
            print("-" * 50)

        return {
            "metrics": metrics,
            "eval_table": eval_table
        }
