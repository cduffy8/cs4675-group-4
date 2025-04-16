from service.models.Api import SearchResponse
from service.models.SearchConfig import SearchConfig

from pydantic import BaseModel
from typing import List

import uuid

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
        
class TestStats:
    def __init__(self, config : SearchConfig):
        self.config : SearchConfig = config
        
        self.total_percision = 0.0
        self.total_recall = 0.0
        self.total_f1_score = 0.0
        self.total_reciprocal_rank = 0.0
        self.total_tests = 0
        
        self.total_hard_percision = 0.0
        self.total_hard_recall = 0.0
        self.total_hard_f1_score = 0.0
        self.total_hard_reciprocal_rank = 0.0
        self.total_hard_tests = 0
        
        self.total_easy_percision = 0.0
        self.total_easy_recall = 0.0
        self.total_easy_f1_score = 0.0
        self.total_easy_reciprocal_rank = 0.0
        self.total_easy_tests = 0
        
    def add_result(self, result: TestResult):
        self.total_percision += result.precision
        self.total_recall += result.recall
        self.total_f1_score += result.f1_score
        self.total_reciprocal_rank += result.reciprocal_rank
        self.total_tests += 1
        
        if result.difficulty == "Hard":
            self.total_hard_percision += result.precision
            self.total_hard_recall += result.recall
            self.total_hard_f1_score += result.f1_score
            self.total_hard_reciprocal_rank += result.reciprocal_rank
            self.total_hard_tests += 1
            
        elif result.difficulty == "Easy":
            self.total_easy_percision += result.precision
            self.total_easy_recall += result.recall
            self.total_easy_f1_score += result.f1_score
            self.total_easy_reciprocal_rank += result.reciprocal_rank
            self.total_easy_tests += 1

    def calculate_stats(self):
        if self.total_tests > 0:
            self.total_percision /= self.total_tests
            self.total_recall /= self.total_tests
            self.total_f1_score /= self.total_tests
            self.total_reciprocal_rank /= self.total_tests
            
        if self.total_hard_tests > 0:
            self.total_hard_percision /= self.total_hard_tests
            self.total_hard_recall /= self.total_hard_tests
            self.total_hard_f1_score /= self.total_hard_tests
            self.total_hard_reciprocal_rank /= self.total_hard_tests
            
        if self.total_easy_tests > 0:
            self.total_easy_percision /= self.total_easy_tests
            self.total_easy_recall /= self.total_easy_tests
            self.total_easy_f1_score /= self.total_easy_tests
            self.total_easy_reciprocal_rank /= self.total_easy_tests
            
    def to_dict(self):
        return {
            "vector_model": self.config.vector_model,
            "vector_size": self.config.vector_size,
            
            "total_percision": self.total_percision,
            "total_recall": self.total_recall,
            "total_f1_score": self.total_f1_score,
            "total_reciprocal_rank": self.total_reciprocal_rank,
            
            "total_hard_percision": self.total_hard_percision,
            "total_hard_recall": self.total_hard_recall,
            "total_hard_f1_score": self.total_hard_f1_score,
            "total_hard_reciprocal_rank": self.total_hard_reciprocal_rank,
            
            "total_easy_percision": self.total_easy_percision,
            "total_easy_recall": self.total_easy_recall,
            "total_easy_f1_score": self.total_easy_f1_score,
            "total_easy_reciprocal_rank": self.total_easy_reciprocal_rank
        }
    