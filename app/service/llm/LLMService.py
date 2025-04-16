from typing import List
import requests
import json

class LLMService:
    def __init__(self, url="http://localhost:11434/api/generate"):
        self.url = url
        
    def generate_queries(self, user_query) -> List[str]:
        format_string = '{"queries": ["query1", "query2", "query3"]}'
        prompt = f"""
        You are a AI assisntant, helping developers to find the Angular.js documentation that they are looking for. You may be provided with a search query or a question from the developer.
        
        You're job is to generate 2-3 search queries that rephase the user's question, so that the search engine can find the most relevant documentation.
        You must return your answer in JSON format, like this:
        {format_string}
        
        The queries should remain within the context of the original question, and should be at most 10 words. The queries should be relevant to Angular.js documentation and if possible.
        You can also take the users questions and convert it into a statement to make it more likely to find the needed results.
        
        Developer Input:
        {user_query}
        """
        
        model_response = self.execute_prompt("llama3.2:1b", prompt)
        print(f"Model response: {model_response.get('response', '')}")
        try:
            queries_object = model_response.get("response", '')
            queries = json.loads(queries_object).get("queries", [])
            if len(queries) > 0:
                return queries
        except Exception as e:
            print(f"Error processing model response: {e}")
            return []
    
    def execute_prompt(self, model, prompt):
        response = requests.post(self.url, json={
            "model": model,
            "prompt": prompt,
            "stream": False
        })
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Error: {response.status_code} - {response.text}")