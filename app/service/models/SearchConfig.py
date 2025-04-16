from typing import List
from pydantic import BaseModel

class SearchConfig(BaseModel):
    vector_model: str
    index_name: str
    vector_size: int

    def __hash__(self):
        return hash((self.vector_model, self.index_name, self.vector_size))

    def __eq__(self, other):
        if not isinstance(other, SearchConfig):
            return NotImplemented
        return (self.vector_model, self.index_name, self.vector_size) == (other.vector_model, other.index_name, other.vector_size)
class SearchConfigs(BaseModel):
    indexes : List[SearchConfig]