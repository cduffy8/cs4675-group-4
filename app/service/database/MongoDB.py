from typing import List
from service.models.Asset import Asset
from pymongo import MongoClient

class CrawlDataCollection:
    def __init__(self, mongo_db_secret):
        self.client = MongoClient(mongo_db_secret)
        self.db = self.client['web_crawler']
        self.collection = self.db['crawl_data_angular']
        
    def get_all(self) -> List[Asset]:
        documents = list(self.collection.find())
        
        return [Asset(doc) for doc in documents]