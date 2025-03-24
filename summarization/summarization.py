import openai
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# change model if needed
def summarize_text(text, model = "gpt-3.5-turbo", max_tokens = 200):
    prompt = "You are a technical assistant for Next.js documentation. Based on the following content extracted from the Next.js website, please generate a clear, concise answer to the user's question while preserving the most important technical details:\n\n" + text

    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "system", "content": prompt}],
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error: {e}")
        return None

# split text into smaller chunks to stay within token limit
def chunk_text(text, max_chunk_size = 1000):
    sentences = text.split('. ')
    chunks = []
    current_chunk = ""
    for sentence in sentences:
        sentence = sentence if sentence.endswith('.') else sentence + "."
        if len(current_chunk) + len(sentence) <= max_chunk_size:
            current_chunk += sentence + " "
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

# summarize chunks and combine
def summarize_chunk(text, model = "gpt-3.5-turbo", max_tokens = 200):
    chunks = chunk_text(text)
    chunk_summaries = []
    for chunk in chunks:
        summary = summarize_text(chunk, model=model, max_tokens=max_tokens)
        if summary:
            chunk_summaries.append(summary)
    combined_text = " ".join(chunk_summaries)
    final_summary = summarize_text(combined_text, model=model, max_tokens=max_tokens)
    return final_summary