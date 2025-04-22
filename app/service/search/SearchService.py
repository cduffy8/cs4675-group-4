from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
import time

from service.llm.LLMService import LLMService
from service.models.SearchConfig import IndexConfig, IndexConfigs
from service.models.Api import SearchRequest, SearchResponseItem, SearchResponse
from service.database.MongoDB import CrawlDataCollection
from service.models.Asset import Asset
from service.vector.VectorService import VectorService

## TODO: Pass an Index Config into this
class InternalIndexSearchRequest(BaseModel):
    query: str
    index_name: str
    top_k: int = 50
    confidence: float = 0.0
    weight: float = 1.0
    vector_model: str
    query_vector: List[float] = []
    results: Optional[List[SearchResponseItem]] = []
    metrics: Dict = {}

class InternalSearchRequest(BaseModel):
    metrics : Dict = {}
    internal_requests: List[InternalIndexSearchRequest] = []
    merge_method: str = "default"

class SearchService:
    def __init__(self, mongo_db_secret: str, search_configs: IndexConfigs, initialize: bool = False, docker : bool = True):
        self.crawl_data_collection : CrawlDataCollection = CrawlDataCollection(mongo_db_secret)
        
        self.vector_services : Dict[str, VectorService] = {}
        for search_config in search_configs.indexes:
            if not search_config.vector_model in self.vector_services:
                self.vector_services[search_config.vector_model] = VectorService(search_config)
            
        self.search_configs : IndexConfigs = search_configs
            
        ## keep this in case the collection gets too big somehow
        if docker:
            self.qdrant_client : QdrantClient = QdrantClient(url="http://localhost:6333")
        else:
            self.qdrant_client : QdrantClient = QdrantClient(location=":memory:")
        
        if initialize:
            self.initialize_indexes()
            
        self.llm_service = LLMService()
           
    ## SKIP 
    def get_index_config(self, index_name: str) -> IndexConfig:
        for config in self.search_configs.indexes:
            if config.index_name == index_name:
                return config
        raise ValueError(f"Index {index_name} not found in search configs")
         
    ## SKIP    
    def initialize_indexes(self):
        assets: List[Asset] = self.crawl_data_collection.get_all()
        for config in self.search_configs.indexes:
            self.qdrant_client.delete_collection(collection_name=config.index_name)
            self.qdrant_client.create_collection(
                collection_name=config.index_name,
                vectors_config=VectorParams(size=config.vector_size, distance=Distance.COSINE),
            )
            
            self.load_index(config.index_name, assets)
            
    ## SKIP 
    def load_index(self, index_name: str, assets: List[Asset]):
        point_structs : List[PointStruct] = []
        
        for item in assets:
            if not item.vectors.get(index_name):
                raise ValueError(f"Vector model {index_name} not found in asset {item.vector_id}")
            point_structs.append(PointStruct(id=item.vector_id, vector=item.vectors[index_name], payload=item.get_qdrant_payload()))
            
        self.qdrant_client.upsert(collection_name=index_name, wait=True, points=point_structs)
        
    ## SKIP
    def generate_queries(self, search_request: SearchRequest) -> List[str]:
        if not search_request.generate_queries:
            return [search_request.query]
        
        generated_queries = self.llm_service.generate_queries(search_request.query)
        if len(generated_queries) > 0:
            print(f"From {search_request.query} Generated queries: {generated_queries}")
        else:
            generated_queries = []
        generated_queries.append(search_request.query)
        
        return generated_queries      
     
    ## TIMED   
    def create_internal_search_request(self, search_request: SearchRequest) -> InternalSearchRequest:
        start_time = time.time()
        # get all of the queries
        queries = self.generate_queries(search_request)
        elapsed_time = time.time() - start_time
        metrics = { "query_generation_time": elapsed_time }
        
        # create the internal search request
        internal_requests = []
        for query in queries:
            internal_requests.extend(self.create_internal_index_search_request_for_query(search_request, query))
            
        return InternalSearchRequest(internal_requests=internal_requests, merge_method=search_request.merge_method, metrics=metrics)
        
    ## TIMED
    def create_internal_index_search_request_for_query(self, search_request: SearchRequest, query : str) -> List[InternalIndexSearchRequest]:
        start_time = time.time()
        index_configs = [self.get_index_config(index_request.index_name) for index_request in search_request.index_requests]
        index_to_model = {index_config.index_name: index_config.vector_model for index_config in index_configs}
        
        # TODO: Move the Vector Caching to the Vector Service
        query_vectors, vectorization_metrics = self.generate_all_query_vectors(index_to_model.values(), query)
        internal_requests : List[InternalIndexSearchRequest] = []
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
        elapsed_time = time.time() - start_time
        vectorization_metrics["total_internal_index_req_time"] = elapsed_time
        
        for index_request in internal_requests:
            index_request.metrics = {**index_request.metrics, **vectorization_metrics}
        return internal_requests
    
    ## TIMED
    def generate_all_query_vectors(self, model_names : List[str], query : str) -> Tuple[Dict[str, List[float]], Dict]:
        metrics = {}
        
        start_time = time.time()
        query_vectors = dict()
        for model in model_names:
            if model in query_vectors:
                continue
            if model not in self.vector_services:
                raise ValueError(f"Vector model {model} not found")
            vector_start_time = time.time()
            query_vectors[model] = self.vector_services[model].generate_vector(query)
            vector_elapsed_time = time.time() - vector_start_time
            metrics[f"{model}_vectorization_time"] = vector_elapsed_time
        
        elapsed_time = time.time() - start_time
        metrics["total_query_vectorization_time"] = elapsed_time
        return query_vectors, metrics
    
    def execute_internal_index_search_request(self, search_request: InternalIndexSearchRequest) -> InternalIndexSearchRequest:
        start_time = time.time()
        index_name = search_request.index_name
        query_vector = search_request.query_vector
        top_k = search_request.top_k
        confidence = search_request.confidence
        
        search_results = self.qdrant_client.query_points(
            collection_name=index_name,
            query=query_vector,
            limit=top_k,
            score_threshold=confidence,
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
        
        elapsed_time = time.time() - start_time
        search_request.metrics[f"{index_name}_search_time_{str(search_request.query.__hash__())}"] = elapsed_time
        return InternalIndexSearchRequest(
            query=search_request.query,
            index_name=index_name,
            top_k=top_k,
            confidence=search_request.confidence,
            weight=search_request.weight,
            vector_model=search_request.vector_model,
            query_vector=query_vector,
            results=results,
            metrics=search_request.metrics
        )
     
    ## SKIP
    # TODO: Efficiency Here   
    def reciprocal_rank_fusion(self, search_requests: List[InternalIndexSearchRequest]) -> List[SearchResponseItem]:
        scores = {}
        for search_request in search_requests:
            for rank, result in enumerate(search_request.results):
                if result.id not in scores:
                    scores[result.id] = 0
                scores[result.id] += 1 / (rank + 1) * search_request.weight
        
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
            # all search result items
        search_result_items_dict : Dict[str, SearchResponseItem] = {}
        for search_request in search_requests:
            for result in search_request.results:
                if result.id not in search_result_items_dict:
                    search_result_items_dict[result.id] = result
                search_result_items_dict[result.id].score += scores[result.id] * search_request.weight
        
        # create a list of SearchResponseItem objects
        merged_results = []
        for id, score in sorted_results:
            if id in search_result_items_dict:
                merged_results.append(SearchResponseItem(
                    id=id,
                    url=search_result_items_dict[id].url,
                    title=search_result_items_dict[id].title,
                    text=search_result_items_dict[id].text,
                    score=score
                ))
        
        # sort the merged results by score
        merged_results.sort(key=lambda x: x.score, reverse=True)
        
        return merged_results
    
    ## SKIP
    def merge_results(self, search_request: InternalSearchRequest, merge_method: str) -> List[SearchResponseItem]:
        if len(search_request.internal_requests) == 1:
            return search_request.internal_requests[0].results
        elif merge_method == "rrf" or merge_method == "default":
            return self.reciprocal_rank_fusion(search_request.internal_requests)
        else:
            print("UNSUPPORTED MERGE METHOD -- USING FIRST")
            return search_request.internal_requests[0].results
        
    def execute_internal_search_request(self, search_request: InternalSearchRequest) -> Tuple[List[SearchResponseItem], Dict]:
        metrics = search_request.metrics
        start_time = time.time()
        updated_index_request = []
        for index_request in search_request.internal_requests:
            updated_index_request.append(self.execute_internal_index_search_request(index_request))
        
        search_request.internal_requests = updated_index_request
        elapsed_time = time.time() - start_time
        metrics["total_internal_search_time"] = elapsed_time
        
        merge_start_time = time.time()
        merge_response :  List[SearchResponseItem] = self.merge_results(search_request, search_request.merge_method)
        merge_elapsed_time = time.time() - merge_start_time
        total_elapsed_time = time.time() - start_time
        metrics["total_merge_time"] = merge_elapsed_time
        metrics["total_search_time"] = total_elapsed_time
        
        for index_request in search_request.internal_requests:
            metrics.update(index_request.metrics)
        
        return merge_response, metrics
    
    def search(self, search_request: SearchRequest) -> SearchResponse:
        start_time = time.time()
        internal_search_request = self.create_internal_search_request(search_request)
        search_response, metrics = self.execute_internal_search_request(internal_search_request)
        
        if len(search_response) > search_request.top_k:
            search_response = search_response[:search_request.top_k]
        elapsed_time = time.time() - start_time
        metrics["total_time"] = elapsed_time
        return SearchResponse(
            request=search_request,
            results=search_response,
            metrics=metrics
        )