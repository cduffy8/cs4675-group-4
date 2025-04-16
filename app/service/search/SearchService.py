from typing import Dict, List, Optional
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance

from service.models.SearchConfig import IndexConfig, IndexConfigs
from service.models.Api import SearchRequest, SearchResponseItem, SearchResponse
from service.database.MongoDB import CrawlDataCollection
from service.models.Asset import Asset
from service.vector.VectorService import VectorService

## TODO: Pass an Index Config into this
class InternalIndexSearchRequest(BaseModel):
    query: str
    index_name: str
    top_k: int = 20
    confidence: float # make optional
    weight: float = 0.0
    vector_model: str
    query_vector: List[float] = []
    results: Optional[List[SearchResponseItem]] = []

class InternalSearchRequest(BaseModel):
    internal_requests: List[InternalIndexSearchRequest] = []
    merge_method: str = "merge"

class SearchService:
    def __init__(self, mongo_db_secret: str, search_configs: IndexConfigs, initialize: bool = True, docker : bool = False):
        self.crawl_data_collection : CrawlDataCollection = CrawlDataCollection(mongo_db_secret)
        
        self.vector_services : Dict[str, VectorService] = {}
        for search_config in search_configs.indexes:
            self.vector_services[search_config.vector_model] = VectorService(search_config)
            
        self.search_configs : IndexConfigs = search_configs
            
        ## keep this in case the collection gets too big somehow
        if docker:
            self.qdrant_client : QdrantClient = QdrantClient(url="http://localhost:6333")
        else:
            self.qdrant_client : QdrantClient = QdrantClient(location=":memory:")
        
        if initialize:
            self.initialize_indexes()
            
    def get_index_config(self, index_name: str) -> IndexConfig:
        for config in self.search_configs.indexes:
            if config.index_name == index_name:
                return config
        raise ValueError(f"Index {index_name} not found in search configs")
            
    def initialize_indexes(self):
        assets: List[Asset] = self.crawl_data_collection.get_all()
        for config in self.search_configs.indexes:
            self.qdrant_client.delete_collection(collection_name=config.index_name)
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
        
    def get_all_queries(self, search_request: SearchRequest) -> List[str]:
        # TODO: Add Model Query Generation Here
        
        queries = [search_request.query]
        return queries
        
    def create_internal_search_request(self, search_request: SearchRequest) -> InternalSearchRequest:
        # get all of the queries
        queries = self.get_all_queries(search_request)
        
        # create the internal search request
        internal_requests = []
        for query in queries:
            internal_requests.extend(self.create_internal_index_search_request_for_query(search_request, query))
            
        return InternalSearchRequest(internal_requests=internal_requests)
        
    def create_internal_index_search_request_for_query(self, search_request: SearchRequest, query : str) -> List[InternalIndexSearchRequest]:
        index_configs = [self.get_index_config(index_request.index_name) for index_request in search_request.index_requests]
        index_to_model = {index_config.index_name: index_config.vector_model for index_config in index_configs}
        
        # TODO: Move the Vector Caching to the Vector Service
        query_vectors = self.generate_all_query_vectors(index_to_model.values(), query)
        internal_requests = []
        for index_request in search_request.index_requests:
            index_config = self.get_index_config(index_request.index_name)
            if index_config.vector_model not in query_vectors:
                raise ValueError(f"Vector model {index_config.vector_model} not found")
            
            internal_requests.append(InternalIndexSearchRequest(
                query=query,
                index_name=index_request.index_name,
                top_k=index_request.top_k,
                confidence=index_request.confidence,
                weight=index_request.weight,
                vector_model=index_config.vector_model,
                query_vector=query_vectors[index_config.vector_model]
            ))
        
        return internal_requests
        
    def generate_all_query_vectors(self, model_names : List[str], query : str) -> Dict[str, List[float]]:
        query_vectors = dict()
        for model in model_names:
            if model in query_vectors:
                continue
            if model not in self.vector_services:
                raise ValueError(f"Vector model {model} not found")
            query_vectors[model] = self.vector_services[model].generate_vector(query)
        
        return query_vectors
    
    def execute_internal_index_search_request(self, search_request: InternalIndexSearchRequest) -> InternalIndexSearchRequest:
        index_name = search_request.index_name
        query_vector = search_request.query_vector
        top_k = search_request.top_k
        
        # TODO: Use the confidence
        confidence = search_request.confidence
        
        search_results = self.qdrant_client.query_points(
            collection_name=index_name,
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
        
        return InternalIndexSearchRequest(
            query=search_request.query,
            index_name=index_name,
            top_k=top_k,
            confidence=search_request.confidence,
            weight=search_request.weight,
            vector_model=search_request.vector_model,
            query_vector=query_vector,
            results=results
        )
    
    def merge_results(self, search_request: InternalSearchRequest, merge_method: str) -> List[SearchResponseItem]:
        ## TODO: Add Merge Methods
        
        if merge_method == "first" or len(search_request.internal_requests) == 1:
            return search_request.internal_requests[0].results
        else:
            print("UNSUPPORTED MERGE METHOD -- USING FIRST")
            return search_request.internal_requests[0].results
        
    def execute_internal_search_request(self, search_request: InternalSearchRequest) -> List[SearchResponseItem]:
        updated_index_request = []
        for index_request in search_request.internal_requests:
            updated_index_request.append(self.execute_internal_index_search_request(index_request))
        
        search_request.internal_requests = updated_index_request
        
        return self.merge_results(search_request, search_request.merge_method)
    
    def search(self, search_request: SearchRequest) -> SearchResponse:
        internal_search_request = self.create_internal_search_request(search_request)
        search_response = self.execute_internal_search_request(internal_search_request)
        
        return SearchResponse(
            request=search_request,
            results=search_response
        )