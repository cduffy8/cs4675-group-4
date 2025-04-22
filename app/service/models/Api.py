from pydantic import BaseModel
from typing import List

class SearchIndexRequest(BaseModel):
    index_name: str
    top_k: int = 50
    confidence: float = 0.0
    weight: float = 1.0

    def __hash__(self):
        return hash((self.index_name, self.top_k, self.confidence, self.weight))

    def __eq__(self, other):
        if not isinstance(other, SearchIndexRequest):
            return False
        return (
            self.index_name == other.index_name and
            self.top_k == other.top_k and
            self.confidence == other.confidence and
            self.weight == other.weight
        )

class SearchRequest(BaseModel):
    query: str
    generate_queries: bool = False
    index_requests: List[SearchIndexRequest]
    top_k : int = 10
    merge_method: str = "default"

class SearchResponseItem(BaseModel):
    id: str
    url: str
    title: str
    text: str
    score: float
    
class SearchResponse(BaseModel):
    request: SearchRequest
    results: List[SearchResponseItem]
    metrics: dict