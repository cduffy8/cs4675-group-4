from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from typing import Optional
from service.models.Api import SearchRequest, SearchResponse
from service.search.SearchService import SearchService
from service.models.SearchConfig import SearchConfigs, SearchConfig

from dotenv import load_dotenv
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Allow your frontend's port
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

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
async def search(query: str, vector_model: str, top_k: int):
    request = SearchRequest(query=query, vector_model=vector_model, top_k=top_k)
    return search_service.search(request)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
