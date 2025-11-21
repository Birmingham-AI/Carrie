#!/usr/bin/env python3
"""Quick test script for the backend API"""

import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from services.rag_service import RAGService

def test_rag_service():
    """Test the RAG service functionality"""
    print("Testing RAG Service...")
    print("=" * 50)

    try:
        # Initialize service
        service = RAGService()
        print("✓ RAG Service initialized")

        # Test search
        test_query = "What is AI?"
        print(f"\nSearching for: '{test_query}'")
        results = service.search_meeting_notes(test_query, top_k=3)
        print(f"✓ Found {len(results)} results")

        if results:
            print("\nTop result:")
            print(f"  Year/Month: {results[0]['year']}/{results[0]['month']}")
            print(f"  Slide: {results[0]['slide']}")
            print(f"  Score: {results[0]['score']:.4f}")
            print(f"  Text: {results[0]['text'][:100]}...")

        print("\n" + "=" * 50)
        print("✓ All tests passed!")
        return True

    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        print("\nMake sure you have:")
        print("1. Run 'python -m backend.actions.bundle' to create bundled embeddings")
        print("2. Set OPENAI_API_KEY in your .env file")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_rag_service()
    sys.exit(0 if success else 1)
