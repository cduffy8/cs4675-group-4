from typing import Dict, List
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance

from service.models.SearchConfig import SearchConfig, SearchConfigs
from service.models.Api import SearchRequest, SearchResponseItem, SearchResponse
from service.database.MongoDB import CrawlDataCollection
from service.models.Asset import Asset
from service.vector.VectorService import VectorService

class SearchService:
    def __init__(self, mongo_db_secret: str, search_configs: SearchConfigs, initialize: bool = True):
        self.crawl_data_collection : CrawlDataCollection = CrawlDataCollection(mongo_db_secret)
        
        self.vector_services : Dict[str, VectorService] = {}
        for search_config in search_configs.indexes:
            self.vector_services[search_config.vector_model] = VectorService(search_config)
            
        self.search_configs : SearchConfigs = search_configs
            
        ## keep this in case the collection gets too big somehow
        # self.qdrant_client : QdrantClient = QdrantClient(url="http://localhost:6333") 
        self.qdrant_client : QdrantClient = QdrantClient(location=":memory:")
        
        if initialize:
            self.initialize_indexes()
            
    def get_search_config(self, index_name: str) -> SearchConfig:
        for config in self.search_configs.indexes:
            if config.index_name == index_name:
                return config
        raise ValueError(f"Index {index_name} not found in search configs")
            
    def initialize_indexes(self):
        assets: List[Asset] = self.crawl_data_collection.get_all()
        for config in self.search_configs.indexes:
            self.qdrant_client.delete_collection(collection_name=config.vector_model)
            self.qdrant_client.create_collection(
                collection_name=config.index_name,
                vectors_config=VectorParams(size=config.vector_size, distance=Distance.COSINE),
            )
            
            self.load_index(config.index_name, assets)
            
    def load_index(self, index_name: str, assets: List[Asset]):
        point_structs : List[PointStruct] = []
        
        for item in assets:
            if not item.vectors.get(index_name):
                raise ValueError(f"Vector model {index_name} not found in asset {item.vector_id}")
            point_structs.append(PointStruct(id=item.vector_id, vector=item.vectors[index_name], payload=item.get_qdrant_payload()))
            
        self.qdrant_client.upsert(collection_name=index_name, wait=True, points=point_structs)
        
    def search(self, search_request: SearchRequest) -> SearchResponse:
        query = search_request.query
        top_k = search_request.top_k
        
        config : SearchConfig  = self.get_search_config(search_request.index_name)
        
        query_vector = self.get_query_vector(query, config.vector_model)
        
        search_results = self.qdrant_client.query_points(
            collection_name=search_request.index_name,
            query=query_vector,
            limit=top_k
        )
        
        points = search_results.points
        
        results = []
        for point in points:
            results.append(SearchResponseItem(
                id=point.id,
                url=point.payload.get('url', ''),
                title=point.payload.get('title', ''),
                text=point.payload.get('text', ''),
                score=point.score
            ))
        
        return SearchResponse(query=query, results=results, vector_model=search_request.index_name)

    def get_query_vector(self, query: str, vector_model: str) -> List[float]:
        if vector_model not in self.vector_services:
            raise ValueError(f"Vector model {vector_model} not found")
        
        return self.vector_services[vector_model].generate_vector(query)