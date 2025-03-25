from pydantic import BaseModel
from typing import List

class SearchRequest(BaseModel):
    query: str
    vector_model: str
    top_k: int
    
class SearchResponseItem(BaseModel):
    id: str
    url: str
    title: str
    text: str
    score: float
    
class SearchResponse(BaseModel):
    query: str
    results: List[SearchResponseItem]
    vector_model: str