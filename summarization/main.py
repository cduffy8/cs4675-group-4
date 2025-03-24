import openai
from pymongo import MongoClient
from summarization import summarize_text, summarize_chunk

# TODO: hide api key
openai.api_key = "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"

# change threshold if needed
def process_document(document):
    html_content = document.get("html", "")
    threshold = 1000

    if len(html_content) > threshold:
        summary = summarize_chunk(html_content)
    else:
        summary = summarize_text(html_content)

    return summary

def main():
    client = MongoClient('mongodb+srv://bxrodgers1:CS4675@cluster0.6u3n5.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
    db = client['web_crawler']
    collection = db['crawl_data']

    document = collection.find_one({"url": "https://nextjs.org/docs/app"})

    if document:
        summary = process_document(document)
        print("AI Generated Response:")
        print(summary)
    else:
        print("Error")

    client.close()

if __name__ == "__main__":
    main()