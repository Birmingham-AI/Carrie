"""
Process PDF slides and create embeddings for RAG using text extraction.

Usage (CLI):
    python -m backend.actions.process_slides --pdf "slides/presentation.pdf" --session "Nov 2024 Birmingham AI Meetup"

Usage (Python):
    from backend.actions.process_slides import SlideProcessor

    processor = SlideProcessor()
    async for chunk in processor.stream_from_bytes(pdf_bytes, "slides.pdf", "Nov 2024 Meetup"):
        print(chunk)
"""

import argparse
import asyncio
import io
import json
import os
import time
from pathlib import Path
from os.path import join, dirname
from typing import AsyncGenerator

from dotenv import load_dotenv
from pypdf import PdfReader

# Load environment variables (for CLI usage)
load_dotenv(join(dirname(dirname(dirname(__file__))), ".env"))

from clients import get_embedding

EMBEDDINGS_DIR = "embeddings"

class SlideProcessor:
    """Process PDF slides using extracted page text and create embeddings for RAG."""

    def __init__(self):
        """Initialize the processor."""

    def _extract_page_text(self, page) -> str:
        """Extract text from a single PDF page."""
        text = page.extract_text()
        return text if text else ""

    async def _get_embedding(self, text: str) -> list[float]:
        """Get embedding for text using shared OpenAI client."""
        return await get_embedding(text)

    async def stream_from_bytes(
        self,
        pdf_bytes: bytes,
        filename: str,
        session_info: str
    ) -> AsyncGenerator[dict, None]:
        """
        Process PDF from bytes using vision and yield each chunk as it's processed.

        This is memory-efficient as it processes one page at a time
        and allows the caller to save each chunk immediately.

        Args:
            pdf_bytes: PDF file content as bytes
            filename: Name of the PDF file (for logging/metadata)
            session_info: Description of the session

        Yields:
            dict: Embedded chunk for each slide with keys:
                - session_info, text, timestamp, embedding
                - page_num: current page number
                - total_pages: total number of pages
        """
        print(f"Processing: {filename}")

        reader = PdfReader(io.BytesIO(pdf_bytes))
        total_pages = len(reader.pages)
        print(f"Found {total_pages} pages")

        for page_num, page in enumerate(reader.pages, start=1):
            start_time = time.time()
            print(f"  Processing Page {page_num}/{total_pages}...", end=" ", flush=True)

            text = self._extract_page_text(page)

            # Skip if no content extracted
            if not text.strip():
                print("Skipped (no content)")
                continue

            # Create embedding
            embedding = await self._get_embedding(text)

            elapsed = time.time() - start_time
            print(f"Done ({elapsed:.2f}s)")

            yield {
                "session_info": session_info,
                "text": text,
                "timestamp": f"Slide {page_num}",
                "embedding": embedding,
                "page_num": page_num,
                "total_pages": total_pages
            }

    async def process_from_bytes(
        self,
        pdf_bytes: bytes,
        filename: str,
        session_info: str
    ) -> list[dict]:
        """
        Process PDF from bytes and return all chunks.

        Args:
            pdf_bytes: PDF file content as bytes
            filename: Name of the PDF file
            session_info: Description of the session

        Returns:
            List of embedded slide chunks
        """
        chunks = []
        async for chunk in self.stream_from_bytes(pdf_bytes, filename, session_info):
            chunks.append(chunk)
        return chunks

    async def process(
        self,
        pdf_path: str,
        session_info: str,
        output_filename: str = None,
        save_local: bool = True
    ) -> list[dict]:
        """
        Process PDF slides from file path and create embeddings.

        Args:
            pdf_path: Path to the PDF file
            session_info: Description of the session
            output_filename: Optional custom output filename
            save_local: Whether to save JSON file locally

        Returns:
            List of embedded slide chunks
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Read file bytes
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        embedded_chunks = await self.process_from_bytes(pdf_bytes, pdf_path.name, session_info)

        # Save to embeddings directory (optional)
        if save_local and embedded_chunks:
            if output_filename is None:
                output_filename = f"slides-{pdf_path.stem}.json"

            if not output_filename.endswith(".json"):
                output_filename += ".json"

            output_path = os.path.join(EMBEDDINGS_DIR, output_filename)
            os.makedirs(EMBEDDINGS_DIR, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(embedded_chunks, f, indent=2, ensure_ascii=False)

            print(f"\nSaved to: {output_path}")

        print(f"Total slides processed: {len(embedded_chunks)}")

        return embedded_chunks


async def async_main():
    parser = argparse.ArgumentParser(
        description="Process PDF slides using text extraction and create embeddings"
    )
    parser.add_argument(
        "--pdf",
        type=str,
        required=True,
        help="Path to PDF file"
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
        help="Output filename (default: slides-{pdf_name}.json)"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Skip saving JSON file locally"
    )
    args = parser.parse_args()

    try:
        pdf_path = Path(args.pdf)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Determine output path
        if args.output:
            output_filename = args.output
        else:
            output_filename = f"slides-{pdf_path.stem}.json"

        if not output_filename.endswith(".json"):
            output_filename += ".json"

        output_path = os.path.join(EMBEDDINGS_DIR, output_filename)
        os.makedirs(EMBEDDINGS_DIR, exist_ok=True)

        # Read PDF bytes
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        # Process and save incrementally
        processor = SlideProcessor()
        chunks = []

        async for chunk in processor.stream_from_bytes(pdf_bytes, pdf_path.name, args.session):
            # Remove page_num and total_pages before saving
            save_chunk = {k: v for k, v in chunk.items() if k not in ("page_num", "total_pages")}
            chunks.append(save_chunk)

            # Save after each slide if not disabled
            if not args.no_save:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(chunks, f, indent=2, ensure_ascii=False)

        print(f"\nTotal slides processed: {len(chunks)}")
        if not args.no_save:
            print(f"Saved to: {output_path}")

    except Exception as e:
        print(f"Error: {e}")
        raise SystemExit(1)


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
