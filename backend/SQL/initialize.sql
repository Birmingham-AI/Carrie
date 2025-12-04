-- Enable pgvector
 CREATE EXTENSION IF NOT EXISTS vector;

 -- Sources table
 CREATE TABLE sources (
   id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
   source_type TEXT NOT NULL,
   source_id TEXT NOT NULL,
   session_info TEXT,
   processed_at TIMESTAMPTZ DEFAULT NOW(),
   chunk_count INT,
   UNIQUE(source_type, source_id)
 );

 -- Embeddings table
 CREATE TABLE embeddings (
   id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
   source_id UUID REFERENCES sources(id) ON DELETE CASCADE,
   text TEXT NOT NULL,
   timestamp TEXT,
   embedding VECTOR(1536)
 );

 -- Index for similarity search
 CREATE INDEX ON embeddings USING hnsw (embedding vector_cosine_ops);


-- Function for similarity search with optional session filter
CREATE OR REPLACE FUNCTION match_embeddings(
    query_embedding VECTOR(1536),
    match_count INT DEFAULT 5,
    session_filter TEXT DEFAULT NULL
  )
  RETURNS TABLE (
    id UUID,
    text TEXT,
    "timestamp" TEXT,
    session_info TEXT,
    similarity FLOAT
  )
  LANGUAGE plpgsql
  AS $$
  BEGIN
    RETURN QUERY
    SELECT
      e.id,
      e.text,
      e."timestamp",
      s.session_info,
      1 - (e.embedding <=> query_embedding) AS similarity
    FROM embeddings e
    JOIN sources s ON e.source_id = s.id
    WHERE session_filter IS NULL OR s.session_info ILIKE '%' || session_filter || '%'
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
  END;
  $$;