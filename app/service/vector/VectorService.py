from sentence_transformers import SentenceTransformer
from typing import List, Tuple
from service.models.SearchConfig import IndexConfig

class VectorService:
    def __init__(self, search_config: IndexConfig):
        self.model_name : str = search_config.vector_model
        self.model : SentenceTransformer = SentenceTransformer(self.model_name, trust_remote_code=True)
        self.embedding_size : int = search_config.vector_size
        
        self.embedding_cache : List[Tuple[str, List[float]]] = []

    def generate_vector(self, text) -> List[float]:
        embedding = self.get_from_cache(text)
        if embedding is not None:
            return embedding
        
        ## can add more logic here to handle different models
        if self.model_name == "nomic-ai/nomic-embed-text-v2-moe":
            embedding =  self.model.encode(text, prompt_name="query")
        else:
            embedding =  self.model.encode(text)
        
        if len(embedding) != self.embedding_size:
            raise ValueError(f"Expected embedding size of {self.embedding_size}, but got {len(embedding)}")
        
        self.add_to_cache(text, embedding)
        
        return embedding
    
    def get_from_cache(self, text) -> List[float]:
        for cached_text, vector in self.embedding_cache:
            if cached_text == text.lower():
                return vector
        return None
    
    def add_to_cache(self, text, vector):
        self.embedding_cache.append((text.lower(), vector))
        if len(self.embedding_cache) > 100:
            self.embedding_cache.pop(0)
