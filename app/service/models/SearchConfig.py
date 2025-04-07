from typing import List
from pydantic import BaseModel

class SearchConfig(BaseModel):
    vector_model: str
    index_name: str
    vector_size: int 
    
class SearchConfigs(BaseModel):
    indexes : List[SearchConfig]