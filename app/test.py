from pymongo import MongoClient
from service.models.Api import SearchRequest, SearchResponse
from service.search.SearchService import SearchService
from service.models.SearchConfig import SearchConfigs, SearchConfig

from dotenv import load_dotenv
import os

from pydantic import BaseModel
from typing import List

import uuid
import json
from pathlib import Path

class TestData:
    def __init__(self, dictionary):
        self.testId = uuid.UUID(dictionary["testId"])
        self.query = dictionary["query"]
        self.answers = [uuid.UUID(answer) for answer in dictionary["answers"]]
        self.difficulty = dictionary["difficulty"]
    
class TestResult(BaseModel):
    testId: uuid.UUID
    query: str
    difficulty: str
    config: SearchConfig
    results: SearchResponse
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    reciprocal_rank: float = 0.0

    def model_dump(self):
        cleaned_results = []
        for result in self.results.results:
            cleaned_results.append({
                "id": result.id,
                "url": result.url,
                "title": result.title,
                "score": result.score
            })
        
        return {
            "config": {
                "vector_model": self.config.vector_model,
                "vector_size": self.config.vector_size
            },
            "results": cleaned_results,
            
            "recall": self.recall,
            "precision": self.precision,
            "f1_score": self.f1_score,
            "reciprocal_rank": self.reciprocal_rank
        }

class TestResults:
    def __init__(self, test_data: TestData):
        self.test_data = test_data
        self.results : List[TestResult] = []
        
    def to_dict(self):
        return {
            "testId": str(self.test_data.testId),
            "query": self.test_data.query,
            "answers": [str(answer) for answer in self.test_data.answers],
            "results": [result.model_dump() for result in self.results]
        }

load_dotenv()

mongo_db_secret = os.getenv("MONGO_DB")

search_configs = SearchConfigs(indexes=[
    SearchConfig(vector_model="all-MiniLM-L6-v2", index_name="all-MiniLM-L6-v2", vector_size=384),
    SearchConfig(vector_model="paraphrase-MiniLM-L6-v2", index_name="paraphrase-MiniLM-L6-v2", vector_size=384),
    SearchConfig(vector_model="all-distilroberta-v1", index_name="all-distilroberta-v1", vector_size=768),
    SearchConfig(vector_model="nomic-ai/nomic-embed-text-v2-moe", index_name= "nomic-embed-text-v2", vector_size=768),
])

print("Loading search service...")
search_service : SearchService = SearchService(mongo_db_secret, search_configs, initialize=True)
print("Search service loaded")

def search(query: str, vector_model: str, top_k: int):
    request = SearchRequest(query=query, index_name=vector_model, top_k=top_k)
    return search_service.search(request)

def load_test_data() -> List[TestData]:
    mongo_db_secret = os.getenv("MONGO_DB")
    mongo_client = MongoClient(mongo_db_secret)
    db = mongo_client["web_crawler"]
    qa_collection = db["generated_qa"]
    
    documents = list(qa_collection.find({}))
    test_data_list : List[TestData] = [TestData(doc) for doc in documents]

    return test_data_list

def calculate_recall(test_data: TestData, test_result: TestResult) -> float:
    relevant_docs = set([str(answer) for answer in test_data.answers])
    retrieved_docs = set(result.id for result in test_result.results.results)
    
    if not relevant_docs:
        return 0.0
    
    true_positives = len(relevant_docs.intersection(retrieved_docs))
    recall = true_positives / len(retrieved_docs)
    
    return recall

def calculate_precision(test_data: TestData, test_result: TestResult) -> float:
    relevant_docs = set([str(answer) for answer in test_data.answers])
    retrieved_docs = set(result.id for result in test_result.results.results)
    
    if not retrieved_docs:
        return 0.0
    
    true_positives = len(relevant_docs.intersection(retrieved_docs))
    precision = true_positives / len(retrieved_docs)
    
    return precision

def calculate_f1_score(test_data: TestData, test_result: TestResult) -> float:
    precision = calculate_precision(test_data, test_result)
    recall = calculate_recall(test_data, test_result)
    
    if precision + recall == 0:
        return 0.0

    f1_score = 2 * (precision * recall) / (precision + recall)
    
    return f1_score

def calculate_reciprocal_rank(test_data: TestData, test_result: TestResult) -> float:
    relevant_docs = set([str(answer) for answer in test_data.answers])
    retrieved_docs = list(result.id for result in test_result.results.results)
    
    if not relevant_docs:
        return 0.0
    
    for index, doc_id in enumerate(retrieved_docs):
        if doc_id in relevant_docs:
            return 1 / (index + 1)
    return 0.0

def calculate_scores(test_data: TestData, test_result: TestResult) -> TestResult:
    test_result.recall = calculate_recall(test_data, test_result)
    test_result.precision = calculate_precision(test_data, test_result)
    test_result.f1_score = calculate_f1_score(test_data, test_result)
    test_result.reciprocal_rank = calculate_reciprocal_rank(test_data, test_result)
    
    return test_result

def save_test_results(test_results: List[TestResults]):
    results_file = Path("test/results.json")
    with open(results_file, "w") as file:
        json.dump([result.to_dict() for result in test_results], file, indent=4)

if __name__ == "__main__":
    test_data : List[TestData] = load_test_data()
    all_test_results : List[TestResults] = []
    
    if not test_data:
        print("No test data found.")
        exit(1)
    
    for item in test_data:
        print(f"Testing {item.query}")
        test_results = TestResults(item)
        for config in search_configs.indexes:
            result = search(item.query, config.index_name, 10)
            test_result = TestResult(
                testId=item.testId,
                query=item.query,
                difficulty=item.difficulty,
                config=config,
                results=result
            )
            test_result = calculate_scores(item, test_result)
            test_results.results.append(test_result)
        all_test_results.append(test_results)
    save_test_results(all_test_results)
    print("Test results saved to test/results.json")
    
    
    ## STAT GENERATION
    scores_per_config = {}

    for test_results in all_test_results:
        for result in test_results.results:
            config_name = result.config.vector_model
            difficulty = result.difficulty
            if config_name not in scores_per_config:
                scores_per_config[config_name] = {
                    "total_f1_score": 0.0,
                    "total_reciprocal_rank": 0.0,
                    "total_results": 0,
                    "hard": {"total_f1_score": 0.0, "total_reciprocal_rank": 0.0, "total_results": 0},
                    "easy": {"total_f1_score": 0.0, "total_reciprocal_rank": 0.0, "total_results": 0}
                }
            scores_per_config[config_name]["total_f1_score"] += result.f1_score
            scores_per_config[config_name]["total_reciprocal_rank"] += result.reciprocal_rank
            scores_per_config[config_name]["total_results"] += 1

            if difficulty.lower() == "hard":
                scores_per_config[config_name]["hard"]["total_f1_score"] += result.f1_score
                scores_per_config[config_name]["hard"]["total_reciprocal_rank"] += result.reciprocal_rank
                scores_per_config[config_name]["hard"]["total_results"] += 1
            elif difficulty.lower() == "easy":
                scores_per_config[config_name]["easy"]["total_f1_score"] += result.f1_score
                scores_per_config[config_name]["easy"]["total_reciprocal_rank"] += result.reciprocal_rank
                scores_per_config[config_name]["easy"]["total_results"] += 1

    for config_name, scores in scores_per_config.items():
        if scores["total_results"] > 0:
            average_f1_score = scores["total_f1_score"] / scores["total_results"]
            mean_reciprocal_rank = scores["total_reciprocal_rank"] / scores["total_results"]
            print(f"Config: {config_name}")
            print(f"  Average F1 Score: {average_f1_score:.4f}")
            print(f"  Mean Reciprocal Rank: {mean_reciprocal_rank:.4f}")
        else:
            print(f"Config: {config_name} has no results to calculate averages.")

        for difficulty in ["hard", "easy"]:
            if scores[difficulty]["total_results"] > 0:
                avg_f1 = scores[difficulty]["total_f1_score"] / scores[difficulty]["total_results"]
                mean_rr = scores[difficulty]["total_reciprocal_rank"] / scores[difficulty]["total_results"]
                print(f"  {difficulty.capitalize()} Cases:")
                print(f"    Average F1 Score: {avg_f1:.4f}")
                print(f"    Mean Reciprocal Rank: {mean_rr:.4f}")
            else:
                print(f"  {difficulty.capitalize()} Cases: No results to calculate averages.")
    exit(0)
            
