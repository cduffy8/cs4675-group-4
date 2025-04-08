from pymongo import MongoClient
import requests
import re
from datetime import datetime

from pymongo.errors import ServerSelectionTimeoutError



# Connect to MongoDB
client = MongoClient('mongodb+srv://bxrodgers1:CS4675@cluster0.6u3n5.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client['web_crawler']
db = client['web_crawler']
source_collection = db['crawl_data']
qa_collection = db["generated_qa"]

# Test connection to MongoDB
try:
    # Ping the server to check connection
    client.admin.command("ping")
    print("Successfully connected to MongoDB")
except ServerSelectionTimeoutError as err:
    print("Failed to connect to MongoDB:", err)
    exit(1)  # exit script early if connection fails

def generate_qa(doc, max_chars=500):  # you can tweak this limit as needed
    """ This generates the question based off the html content and then uploads the question and answer to the generated_qa MongoDB collection. I changed the prompt depending on difficulty of the questions:

    Easy:From the following HTML documentation, generate exactly 1 developer focused question that is explicitly answered in the text. This question should be very straightforward. 

    Hard: From the following HTML documentation, generate exactly 1 helpful developer-focused question and its correct answer. This question should be based on the content and help someone understand it better. """
    html_content = doc.get('html', '')

    # Truncate HTML if it's too long
    if len(html_content) > max_chars:
        print(f"⚠️ Truncating HTML for doc {doc.get('title')}")
        html_content = html_content[:max_chars]

    prompt = f"""
    From the following HTML documentation, generate exactly 1 developer focused question that is explicitly answered in the text. This question should be very straightforward.

    Use markdown format like this:

    **Your question here?**  
    Your answer here.

    Documentation:
    {html_content}
    """

    response = requests.post("http://localhost:11434/api/generate", json={
        "model": "mistral",
        "prompt": prompt,
        "stream": False
    })

    markdown_text = response.json().get("response", "")
    qa_pairs = parse_qa(markdown_text)

    for pair in qa_pairs:
        pair.update({
            "source_id": doc["_id"],
            "source_url": doc.get("url"),
            "created_at": datetime.utcnow(),
            "difficulty": "Easy" ##Change this value depending on the difficulty of the question
        })

    if qa_pairs:
        qa_collection.insert_many(qa_pairs)
        print(f"Stored 1 Q&A for: {doc.get('title')}")

    return markdown_text


# Parse markdown Q&A into structured format
def parse_qa(markdown_text):
    qa_pairs = []
    matches = re.findall(r"\*\*(.+?)\*\*\s*(.*?)(?=\n\*\*|$)", markdown_text, re.DOTALL)

    for question, answer in matches:
        qa_pairs.append({
            "question": question.strip(),
            "answer": answer.strip()
        })

    return qa_pairs

# Main function
def process_documents():
    docs = source_collection.find()
    for doc in docs:
        generate_qa(doc)

if __name__ == "__main__":
    process_documents()