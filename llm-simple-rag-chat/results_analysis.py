import json
from pathlib import Path
import pandas as pd
from collections import defaultdict

def analyze_evaluation_results(results_folder):
    results_dir = Path(results_folder)
    if not results_dir.exists():
        print(f"Error: Results directory {results_dir} does not exist")
        return

    # Process each result file
    for result_file in sorted(results_dir.glob("*.json")):
        try:
            with open(result_file, 'r') as f:
                data = json.load(f)

            # Get file metadata
            timestamp = data["metadata"]["timestamp"]
            model = data["metadata"]["model"]
            mode = data["metadata"]["mode"]
            source_file = data["metadata"].get("source_file", "N/A")

            print(f"\n=== Results for {result_file.name} ===")
            print(f"Timestamp: {timestamp}")
            print(f"Model: {model}")
            print(f"Mode: {mode}")
            print(f"Source file: {source_file}")

            # Initialize statistics for this file
            file_stats = defaultdict(lambda: {"total_weight": 0, "total_score": 0, "questions": []})
            file_scores = []

            # Process auto mode results
            if "categories" in data:
                for category, category_data in data["categories"].items():
                    for question in category_data["questions"]:
                        # Calculate normalized relevance score using Flesch-Kincaid grade level
                        metrics = question["eval_results"]["metrics"]
                        # Normalize Flesch-Kincaid grade level to 0-1 range (lower is better)
                        fk_grade = metrics.get("flesch_kincaid_grade_level/v1/mean", 12.0)  # Default to 12 if not found
                        # Convert grade level to a score where 0-3 is excellent (1.0), 4-6 is good (0.75), 7-9 is fair (0.5), 10+ is poor (0.25)
                        if fk_grade <= 3:
                            relevance_score = 1.0
                        elif fk_grade <= 6:
                            relevance_score = 0.75
                        elif fk_grade <= 9:
                            relevance_score = 0.5
                        else:
                            relevance_score = 0.25
                        
                        # Add to category statistics
                        file_stats[category]["total_weight"] += question["weight"]
                        file_stats[category]["total_score"] += relevance_score * question["weight"]
                        
                        file_stats[category]["questions"].append({
                            "question": question["question"],
                            "score": relevance_score,
                            "weight": question["weight"],
                            "fk_grade": fk_grade
                        })
                        
                        file_scores.append(relevance_score)

            # Process interactive mode results
            elif "questions" in data:
                for question in data["questions"]:
                    metrics = question["eval_results"]["metrics"]
                    relevance_score = metrics.get("exact_match/v1", 0.0)
                    
                    file_stats["Interactive"]["total_weight"] += 1.0  # Interactive mode uses equal weights
                    file_stats["Interactive"]["total_score"] += relevance_score
                    file_stats["Interactive"]["questions"].append({
                        "question": question["question"],
                        "score": relevance_score,
                        "weight": 1.0
                    })
                    
                    file_scores.append(relevance_score)

            # Print file-level statistics
            print("\n=== File Statistics ===")
            print(f"Total questions: {sum(len(v['questions']) for v in file_stats.values())}")
            print(f"Average score: {sum(file_scores)/len(file_scores):.3f}")

            # Create DataFrame for file-level statistics
            file_df = pd.DataFrame({
                "Category": [],
                "Questions": [],
                "Average Score": [],
                "Weighted Score": []
            })

            # Print per-category statistics for this file
            for category, stats in file_stats.items():
                if stats["total_weight"] == 0:
                    continue

                avg_score = stats["total_score"] / len(stats["questions"])
                weighted_score = stats["total_score"] / stats["total_weight"]

                # Add to DataFrame
                file_df = pd.concat([
                    file_df,
                    pd.DataFrame({
                        "Category": [category],
                        "Questions": [len(stats["questions"])],
                        "Average Score": [avg_score],
                        "Weighted Score": [weighted_score]
                    })
                ], ignore_index=True)

                # Print detailed category information
                print(f"\nCategory: {category}")
                print(f"Questions evaluated: {len(stats['questions'])}")
                print(f"Average score: {avg_score:.3f}")
                print(f"Weighted score: {weighted_score:.3f}")

            # Print file-level statistics table
            print("\n=== Detailed Statistics by Category ===")
            print(file_df.to_string(index=False))

            # Print score distribution for this file
            if file_scores:
                print("\n=== Score Distribution ===")
                print(f"Min score: {min(file_scores):.3f}")
                print(f"Max score: {max(file_scores):.3f}")
                print(f"Mean score: {sum(file_scores)/len(file_scores):.3f}")

        except Exception as e:
            print(f"Error processing {result_file}: {str(e)}")
