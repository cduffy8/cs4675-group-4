import uuid

class Asset:
    def __init__(self, doc):
        self.doc = doc
        self.mongodb_id = doc.get('_id')
        self.vector_id = doc.get('vector_id')
        self.url = doc.get('url')
        self.title = doc.get('title')
        self.text = doc.get('html')
        self.summary = doc.get('summary')
        self.vectors = dict()
        self.vectors['all-MiniLM-L6-v2'] = doc.get('all-MiniLM-L6-v2')
        self.vectors['all-distilroberta-v1'] = doc.get('all-distilroberta-v1')
        self.vectors['paraphrase-MiniLM-L6-v2'] = doc.get('paraphrase-MiniLM-L6-v2')

    def __str__(self):
        return f"Asset {self.vector_id}: {self.title} ({self.url}) \n {self.text}"

    def __repr__(self):
        return self.__str__()

    def to_dict(self):
        return {
            "vector_id": self.vector_id,
            "url": self.url,
            "title": self.title,
            "text": self.text,
            "all-MiniLM-L6-v2": self.vectors['all-MiniLM-L6-v2'],
            "all-distilroberta-v1": self.vectors['all-distilroberta-v1'],
            "paraphrase-MiniLM-L6-v2": self.vectors['paraphrase-MiniLM-L6-v2'],
        }
        
    def get_qdrant_payload(self):
        return {
            "id": self.vector_id,
            "url": self.url,
            "title": self.title,
            "text": self.text,
        }