from pandas import read_json
from dotenv import load_dotenv
from os.path import join, dirname
from os import getenv
from openai import OpenAI
import numpy as np
import sys
from pathlib import Path
import re

sys.stdout.reconfigure(encoding='utf-8')

load_dotenv(join(dirname(dirname(__file__)), ".env"))

OPENAI_API_KEY = getenv("OPENAI_API_KEY")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
EMBEDDINGS_DIR = PROJECT_ROOT / "embeddings"
BUNDLED_DIR = EMBEDDINGS_DIR / "bundled"
BUNDLE_FILE_PATTERN = re.compile(r"^bundle-(\d+)\.json$")

client = OpenAI(api_key=OPENAI_API_KEY)

def get_embeddings_file():
    existing = [BUNDLE_FILE_PATTERN.match(path.name) for path in BUNDLED_DIR.glob("bundle-*.json")]
    indices = [int(match.group(1)) for match in existing if match]
    return BUNDLED_DIR / f"bundle-{max(indices, default=0)}.json"


def get_embedding(text):
    resp = client.embeddings.create(model="text-embedding-3-large", input=text)
    return resp.data[0].embedding

def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors"""
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def search_meeting_notes(query, top_k=5):
    """
    Search meeting notes using vector similarity
    
    Args:
        query (str): The search query
        top_k (int): Number of top results to return
        
    Returns:
        list: Top matching results with scores
    """
    # Get query embedding
    query_embedding = get_embedding(query)
    
    # Load embedded meeting notes
    meeting_data = read_json(get_embeddings_file())
    
    # Calculate similarity scores
    results = []
    for index, row in meeting_data.iterrows():
        similarity = cosine_similarity(query_embedding, row['embedding'])
        results.append({
            'slide': row['slide'],
            'year': row['year'],
            'month': row['month'],
            'text': row['text'],
            'score': similarity
        })
    
    # Sort by similarity score (descending)
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return results[:top_k]

# Main execution
if __name__ == "__main__":
    print("Meeting Notes Search")
    print("=" * 50)
    
    query = input("\nEnter your question: ")
    
    print(f"\nSearching for: {query}\n")
    results = search_meeting_notes(query)
    
    print("Top Results:")
    print("-" * 50)
    for i, result in enumerate(results, 1):
        print(f"\n{i}. [Score: {result['score']:.4f}]")
        print(f"   Slide: {result['slide']}")
        print(f"   Year: {result['year']}")
        print(f"   Month: {result['month']}")
        print(f"   Text: {result['text']}")

