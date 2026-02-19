"""
Transcribe YouTube videos and create embeddings for RAG.

Usage (CLI):
    python -m backend.actions.transcribe_youtube --url "VIDEO_URL" --session "Nov 2024 Birmingham AI Meetup"

Usage (Python):
    from backend.actions.transcribe_youtube import YouTubeTranscriber

    transcriber = YouTubeTranscriber()
    result = await transcriber.transcribe("VIDEO_URL", session_info="Nov 2024 Birmingham AI Meetup")

    # Custom settings (overlap is number of sentences)
    transcriber = YouTubeTranscriber(chunk_size=800, overlap=2)
"""

import argparse
import asyncio
import json
import logging
import os
import re
from os.path import join, dirname

from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi

# Load environment variables (for CLI usage)
load_dotenv(join(dirname(dirname(dirname(__file__))), ".env"))

from clients import get_embedding

logger = logging.getLogger(__name__)

EMBEDDINGS_DIR = "embeddings"


class YouTubeTranscriber:
    """Transcribe YouTube videos and create embeddings for RAG."""

    DEFAULT_CHUNK_SIZE = 1000
    DEFAULT_OVERLAP = 1  # Number of sentences to overlap
    DEFAULT_LANGUAGE = "en"

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_OVERLAP,
        language: str = DEFAULT_LANGUAGE
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.language = language
        self._api = YouTubeTranscriptApi()

    @staticmethod
    def extract_video_id(url: str) -> str | None:
        """Extract the video ID from a YouTube URL."""
        patterns = [
            r'(?:v=)([0-9A-Za-z_-]{11})',
            r'(?:youtu\.be/)([0-9A-Za-z_-]{11})',
            r'(?:embed/)([0-9A-Za-z_-]{11})',
            r'(?:shorts/)([0-9A-Za-z_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        if re.match(r'^[0-9A-Za-z_-]{11}$', url):
            return url

        return None

    def _fetch_transcript(self, video_id: str) -> list[dict]:
        """Fetch raw transcript from YouTube."""
        transcript = self._api.fetch(video_id, languages=[self.language])
        return transcript.to_raw_data()

    def _build_char_to_time_map(self, transcript: list[dict]) -> tuple[str, list[tuple[int, float]]]:
        """Build full text and mapping from character positions to timestamps."""
        char_to_time = []
        full_text_parts = []
        char_position = 0

        for entry in transcript:
            char_to_time.append((char_position, entry['start']))
            full_text_parts.append(entry['text'])
            char_position += len(entry['text']) + 1

        return " ".join(full_text_parts), char_to_time

    def _get_time_for_char_position(self, char_pos: int, char_to_time: list[tuple[int, float]]) -> float:
        """Find the timestamp for a given character position."""
        result_time = char_to_time[0][1] if char_to_time else 0.0
        for pos, time in char_to_time:
            if pos <= char_pos:
                result_time = time
            else:
                break
        return result_time

    @staticmethod
    def _split_into_sentences(text: str) -> list[str]:
        """Split text into sentences."""
        pattern = r'(?<=[.!?])\s+'
        sentences = re.split(pattern, text)
        return [s.strip() for s in sentences if s.strip()]

    async def _get_embedding(self, text: str) -> list[float]:
        """Get embedding for text using shared OpenAI client."""
        return await get_embedding(text)

    async def transcribe(
        self,
        url: str,
        session_info: str,
        output_filename: str = None,
        save_local: bool = True
    ) -> list[dict]:
        """
        Transcribe YouTube video and create embeddings directly.

        Args:
            url: YouTube video URL or video ID
            session_info: Description of the session
            output_filename: Optional custom output filename
            save_local: Whether to save JSON file locally (default: True)

        Returns:
            List of embedded chunks
        """
        video_id = self.extract_video_id(url)
        if not video_id:
            raise ValueError(f"Could not extract video ID from: {url}")

        logger.info(f"Fetching transcript for: {video_id}")
        transcript = self._fetch_transcript(video_id)
        full_text, char_to_time = self._build_char_to_time_map(transcript)
        sentences = self._split_into_sentences(full_text)

        logger.info(f"Processing {len(sentences)} sentences into chunks...")

        # Process chunks and embed directly
        embedded_chunks = []
        current_chunk = []
        current_length = 0
        chunk_index = 0
        char_position = 0
        chunk_start_char = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            # If chunk is full, embed and save it
            if current_length + sentence_length > self.chunk_size and current_chunk:
                chunk_text = " ".join(current_chunk)
                start_time = self._get_time_for_char_position(chunk_start_char, char_to_time)
                start_seconds = int(start_time)

                logger.info(f"  Embedding chunk {chunk_index + 1}...")
                embedding = await self._get_embedding(chunk_text)

                embedded_chunks.append({
                    "session_info": session_info,
                    "text": chunk_text,
                    "timestamp": f"https://www.youtube.com/watch?v={video_id}&t={start_seconds}s",
                    "embedding": embedding
                })
                logger.info("Done")

                chunk_index += 1

                # Overlap: keep last N sentences
                overlap_sentences = current_chunk[-self.overlap:] if len(current_chunk) >= self.overlap else current_chunk
                overlap_length = sum(len(s) + 1 for s in overlap_sentences)

                current_chunk = overlap_sentences.copy()
                current_length = overlap_length
                chunk_start_char = char_position - overlap_length

            current_chunk.append(sentence)
            current_length += sentence_length + 1
            char_position += sentence_length + 1

        # Don't forget the last chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            start_time = self._get_time_for_char_position(chunk_start_char, char_to_time)
            start_seconds = int(start_time)

            logger.info(f"  Embedding chunk {chunk_index + 1}...")
            embedding = await self._get_embedding(chunk_text)

            embedded_chunks.append({
                "session_info": session_info,
                "text": chunk_text,
                "timestamp": f"https://www.youtube.com/watch?v={video_id}&t={start_seconds}s",
                "embedding": embedding
            })
            logger.info("Done")

        # Save to embeddings directory (optional)
        if save_local:
            if output_filename is None:
                output_filename = f"youtube-{video_id}.json"

            if not output_filename.endswith('.json'):
                output_filename += '.json'

            output_path = os.path.join(EMBEDDINGS_DIR, output_filename)
            os.makedirs(EMBEDDINGS_DIR, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(embedded_chunks, f, indent=2, ensure_ascii=False)

            logger.info(f"\nSaved to: {output_path}")

        logger.info(f"Total chunks: {len(embedded_chunks)}")

        return embedded_chunks


async def async_main():
    parser = argparse.ArgumentParser(
        description="Transcribe YouTube videos and create embeddings for RAG"
    )
    parser.add_argument(
        "--url",
        type=str,
        required=True,
        help="YouTube video URL or video ID"
    )
    parser.add_argument(
        "--session",
        type=str,
        required=True,
        help="Session info (e.g., 'Nov 2024 Birmingham AI Meetup')"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output filename (default: youtube-{video_id}.json)"
    )
    parser.add_argument(
        "--lang",
        type=str,
        default=YouTubeTranscriber.DEFAULT_LANGUAGE,
        help=f"Language code (default: {YouTubeTranscriber.DEFAULT_LANGUAGE})"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=YouTubeTranscriber.DEFAULT_CHUNK_SIZE,
        help=f"Chunk size in characters (default: {YouTubeTranscriber.DEFAULT_CHUNK_SIZE})"
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=YouTubeTranscriber.DEFAULT_OVERLAP,
        help=f"Sentences to overlap (default: {YouTubeTranscriber.DEFAULT_OVERLAP})"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Skip saving JSON file locally (useful when uploading directly to Supabase)"
    )

    args = parser.parse_args()

    try:
        transcriber = YouTubeTranscriber(
            chunk_size=args.chunk_size,
            overlap=args.overlap,
            language=args.lang
        )
        await transcriber.transcribe(args.url, args.session, args.output, save_local=not args.no_save)
    except Exception as e:
        logger.error(f"Error: {e}")
        raise SystemExit(1)


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
