from pymongo import MongoClient
from service.models.Api import SearchRequest, SearchResponse, SearchResponseItem
from service.search.SearchService import SearchService
from service.models.SearchConfig import SearchConfigs, SearchConfig
from service.models.Test import TestData, TestResult, TestResults, TestStats

from dotenv import load_dotenv
import os

from typing import Dict, List

import json
from pathlib import Path

import requests

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

search_configs.indexes.append(SearchConfig(vector_model="ANGULAR_JS_SEARCH", index_name= "ANGULAR_JS_SEARCH", vector_size=768))

# allow you to map the next js results to the vector ids
def get_document_uid_map():
    mongo_client = MongoClient(mongo_db_secret)
    db = mongo_client["web_crawler"]
    crawl_collection = db["crawl_data_angular"]
    
    documents = list(crawl_collection.find({}))
    vector_id_path_map = {}
    for document in documents:
        url = document["url"]
        vector_id = document["vector_id"]
        vector_id_path_map[url] = vector_id
        
    return vector_id_path_map

def make_angular_request(query: str) -> dict:
    base_url = "https://l1xwt2uj7f-dsn.algolia.net/1/indexes/*/queries"
    parameters = {
        "x-algolia-agent": "Algolia for JavaScript (4.10.5); Browser (lite)",
        "x-algolia-api-key": "dfca7ed184db27927a512e5c6668b968",
        "x-algolia-application-id": "L1XWT2UJ7F"
    }

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "requests":[
            {
                "indexName":"angular_v17",
                "type": "default",
                "query": query,
            }
        ]
    }

    return requests.post(base_url, headers=headers, params=parameters, json=payload).json()

def get_angular_results(query: str, path_map: dict) -> SearchResponse:
    response = make_angular_request(query)
    
    hits = response['results'][0]['hits']

    search_response_items = []
    for hit in hits:
        vector_id = path_map.get(hit["url"].split("#")[0], None)
        if vector_id is None:
            print(f"WARNING: Path not found in path_map: {hit['url']}")
            continue
        
        content = hit.get("content", "failed to get content")
        content = str(content)
        search_response_items.append(SearchResponseItem(
            id=vector_id,
            url=hit['url'],
            title=content,
            text=content,
            score=0.0 # Placeholder for score
        ))
    
    search_response = SearchResponse(
        query=query,
        results=search_response_items,
        vector_model="ANGULAR_JS_SEARCH"
    )
    
    return search_response

path_map = get_document_uid_map()
def search(query: str, vector_model: str, top_k: int):
    if vector_model == "ANGULAR_JS_SEARCH":
        return get_angular_results(query, path_map)
    request = SearchRequest(query=query, index_name=vector_model, top_k=top_k)
    return search_service.search(request)

def load_test_data() -> List[TestData]:
    mongo_db_secret = os.getenv("MONGO_DB")
    mongo_client = MongoClient(mongo_db_secret)
    db = mongo_client["web_crawler"]
    qa_collection = db["generated_qa_angular"]
    
    documents = list(qa_collection.find({}))
    test_data_list : List[TestData] = [TestData(doc) for doc in documents]

    return test_data_list

def get_test_results(test_data: TestData, configs: SearchConfigs) -> TestResults:
    test_results = TestResults(test_data)
    for config in configs.indexes:
        result = search(test_data.query, config.index_name, 10)
        test_result = TestResult(
            testId=test_data.testId,
            query=test_data.query,
            difficulty=test_data.difficulty,
            config=config,
            results=result
        )
        test_result = calculate_scores(test_data, test_result)
        test_results.results.append(test_result)
        
    return test_results

def calculate_recall(test_data: TestData, test_result: TestResult) -> float:
    relevant_docs = set([str(answer) for answer in test_data.answers])
    retrieved_docs = set(result.id for result in test_result.results.results)
    
    if not len(retrieved_docs):
        return 0.0
    
    true_positives = len(relevant_docs.intersection(retrieved_docs))
    recall = true_positives / len(retrieved_docs)
    
    return recall

def calculate_precision(test_data: TestData, test_result: TestResult) -> float:
    relevant_docs = set([str(answer) for answer in test_data.answers])
    retrieved_docs = set(result.id for result in test_result.results.results)
    
    if not len(retrieved_docs):
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

def save_test_results(test_results: List[TestResults], test_stats: List[TestStats]):
    results_file = Path("test/results.json")
    with open(results_file, "w") as file:
        json.dump([result.to_dict() for result in test_results], file, indent=4)
    print("Test results saved to test/results.json")
    stats_file = Path("test/stats.json")
    with open(stats_file, "w") as file:
        json.dump([stats.to_dict() for stats in test_stats], file, indent=4)
    print("Test stats saved to test/stats.json")
    
def calculate_test_stats(all_test_results: List[TestResults]) -> List[TestStats]:
    stats_dict : Dict[SearchConfig, TestStats] = dict()
    
    for test_results in all_test_results:
        for result in test_results.results:
            if result.config not in stats_dict:
                stats_dict[result.config] = TestStats(result.config)
                
            stats_dict[result.config].add_result(result)
            
    for config, stats in stats_dict.items():
        stats.calculate_stats()
    
    return list(stats_dict.values())
 
if __name__ == "__main__":
    test_data : List[TestData] = load_test_data()
    all_test_results : List[TestResults] = []
    
    if not test_data:
        print("No test data found.")
        exit(1)
    
    ## RUN TEST QUERIES
    for index, item in enumerate(test_data):
        print(f'Test {index + 1}/{len(test_data)} -- "{item.query}"')
        test_results = get_test_results(item, search_configs)
        all_test_results.append(test_results)
    
    test_stats = calculate_test_stats(all_test_results)
    save_test_results(all_test_results, test_stats)
    exit(0)
            
