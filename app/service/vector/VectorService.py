from sentence_transformers import SentenceTransformer
from typing import List
from service.models.SearchConfig import SearchConfig

class VectorService:
    def __init__(self, search_config: SearchConfig):
        self.model_name : str = search_config.vector_model
        self.model : SentenceTransformer = SentenceTransformer(self.model_name, trust_remote_code=True)
        self.embedding_size : int = search_config.vector_size

    def generate_vector(self, text) -> List[float]:
        ## can add more logic here to handle different models
        if self.model_name == "nomic-ai/nomic-embed-text-v2-moe":
            embedding =  self.model.encode(text, prompt_name="query")
        else:
            embedding =  self.model.encode(text)
        
        if len(embedding) != self.embedding_size:
            raise ValueError(f"Expected embedding size of {self.embedding_size}, but got {len(embedding)}")
        
        return embedding
