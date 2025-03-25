import uuid

class Asset:
    def __init__(self, doc):
        self.doc = doc
        self.mongodb_id = doc.get('_id')
        self.id = str(uuid.uuid4())
        self.url = doc.get('url')
        self.title = doc.get('title')
        self.text = doc.get('html')
        self.vectors = dict()
        self.vectors['all-MiniLM-L6-v2'] = doc.get('allMiniLML6v2')
        self.vectors['all-distilroberta-v1'] = doc.get('distilrobertav1')
        self.vectors['paraphrase-MiniLM-L6-v2'] = doc.get('paraphraseMiniLML6v2')

    def __str__(self):
        return f"Asset {self.id}: {self.title} ({self.url}) \n {self.text}"

    def __repr__(self):
        return self.__str__()

    def to_dict(self):
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "text": self.text,
            "all-MiniLM-L6-v2": self.vectors['all-MiniLM-L6-v2'],
            "all-distilroberta-v1": self.vectors['all-distilroberta-v1'],
            "paraphrase-MiniLM-L6-v2": self.vectors['paraphrase-MiniLM-L6-v2'],
        }
        
    def get_qdrant_payload(self):
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "text": self.text,
        }