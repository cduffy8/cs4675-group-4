from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from typing import Optional
from service.models.Api import SearchRequest, SearchResponse
from service.search.SearchService import SearchService
from service.models.SearchConfig import IndexConfigs, IndexConfig

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

search_configs = IndexConfigs(indexes=[
    IndexConfig(vector_model="all-MiniLM-L6-v2", index_name="all-MiniLM-L6-v2", vector_size=384),
    IndexConfig(vector_model="paraphrase-MiniLM-L6-v2", index_name="paraphrase-MiniLM-L6-v2", vector_size=384),
    IndexConfig(vector_model="all-distilroberta-v1", index_name="all-distilroberta-v1", vector_size=768),
    IndexConfig(vector_model="nomic-ai/nomic-embed-text-v2-moe", index_name= "nomic-embed-text-v2", vector_size=768),
])

print("Loading search service...")
search_service : SearchService = SearchService(mongo_db_secret, search_configs)
print("Search service loaded")

@app.get("/search")
async def search(query: str, index_name: str, top_k: int):
    request = SearchRequest(query=query, index_name=index_name, top_k=top_k)
    return search_service.search(request)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
