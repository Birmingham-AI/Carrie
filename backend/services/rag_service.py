from typing import List, Dict

from clients import get_supabase, get_embedding


def escape_sql_wildcards(text: str) -> str:
    """Escape wildcard characters for LIKE/ILIKE clauses."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class RAGService:
    """Service for RAG operations: embedding and search"""

    async def list_sessions(self, filter_term: str = None) -> List[Dict]:
        """
        List available sessions from the sources table.

        Args:
            filter_term: Optional filter to narrow results (e.g., "November", "Engineering", "2025")

        Returns:
            List of sessions with session_info and chunk_count
        """
        supabase = await get_supabase()

        query = supabase.table("sources").select("session_info, chunk_count, processed_at").order("processed_at", desc=True)

        if filter_term:
            sanitized_filter = escape_sql_wildcards(filter_term)
            query = query.ilike("session_info", f"%{sanitized_filter}%")

        results = await query.execute()

        return [
            {
                "session_info": row["session_info"],
                "chunk_count": row["chunk_count"],
                "processed_at": row["processed_at"]
            }
            for row in results.data
            if row["session_info"]  # Filter out null session_info
        ]

    async def search_meeting_notes(self, query: str, top_k: int = 5, session_filter: str = None) -> List[Dict]:
        """
        Search meeting notes using vector similarity via Supabase.

        Args:
            query: The search query
            top_k: Number of top results to return
            session_filter: Optional filter for session (e.g., "August 2025", "Breakout", "General meetup")

        Returns:
            List of top matching results with scores
        """
        query_embedding = await get_embedding(query)
        supabase = await get_supabase()

        # Build RPC params
        rpc_params = {
            "query_embedding": query_embedding,
            "match_count": top_k
        }
        if session_filter:
            rpc_params["session_filter"] = escape_sql_wildcards(session_filter)

        # Use Supabase RPC for vector similarity search
        results = await supabase.rpc("match_embeddings", rpc_params).execute()

        return [
            {
                "text": row["text"],
                "timestamp": row["timestamp"],
                "session_info": row["session_info"],
                "score": row["similarity"]
            }
            for row in results.data
        ]
