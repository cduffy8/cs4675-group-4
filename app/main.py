from fastapi import FastAPI, HTTPException

from typing import Optional
from service.models.Api import SearchRequest, SearchResponse
from service.search.SearchService import SearchService
from service.models.SearchConfig import SearchConfigs, SearchConfig

from dotenv import load_dotenv
import os

app = FastAPI()

load_dotenv()

mongo_db_secret = os.getenv("MONGO_DB")

search_configs = SearchConfigs(indexes=[
    SearchConfig(vector_model="all-MiniLM-L6-v2", vector_size=384),
    SearchConfig(vector_model="paraphrase-MiniLM-L6-v2", vector_size=384),
    SearchConfig(vector_model="all-distilroberta-v1", vector_size=768),
])

print("Loading search service...")
search_service : SearchService = SearchService(mongo_db_secret, search_configs)
print("Search service loaded")

@app.get("/search")
async def search(request: SearchRequest) -> SearchResponse:
    return search_service.search(request)
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
