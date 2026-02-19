"""
Process PDF slides and create embeddings for RAG using GPT-4o Vision.

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
import base64
import json
import os
import io
import re
import time
from pathlib import Path
from os.path import join, dirname
from typing import AsyncGenerator

import fitz  # PyMuPDF - used only for PDF to image conversion
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pypdf import PdfReader

# Load environment variables (for CLI usage)
load_dotenv(join(dirname(dirname(dirname(__file__))), ".env"))

from clients import get_embedding

EMBEDDINGS_DIR = "embeddings"

# OpenAI model for vision analysis
VISION_MODEL = "gpt-4.1"

# DPI for rendering PDF pages as images (higher = better quality but larger)
RENDER_DPI = 250

# The prompt for slide analysis via vision
VISION_PROMPT = """Analyze this slide image thoroughly and extract ALL information visible.

Focus on:
- The slide title or heading
- All text content, including bullet points, annotations, footnotes, and captions
- Text inside diagrams, flowcharts, architecture diagrams, or images
- Data from tables, charts, or graphs (include actual numbers and labels)
- Code snippets or technical terms
- Speaker notes if visible
- Any URLs, references, or citations shown

Return as JSON with:
- "slide_title": the title or main heading of the slide (or "Untitled" if none)
- "key_points": an array of strings, each being a distinct piece of information from the slide
- "raw_text": any additional text content not captured in key_points

Be exhaustive. Capture every piece of visible text and data. This content will be used to answer questions about the presentation later, so completeness matters more than brevity.
Do not hallucinate or add information not visible on the slide.
Ensure the JSON is valid and well-formed.
"""


class SlideProcessor:
    """Process PDF slides using GPT-4o Vision and create embeddings for RAG."""

    def __init__(self, dpi: int = RENDER_DPI):
        """
        Initialize the processor.

        Args:
            dpi: Resolution for rendering PDF pages (default: 150)
        """
        self._openai_client: AsyncOpenAI | None = None
        self.dpi = dpi

    def _get_openai(self) -> AsyncOpenAI:
        """Get or create async OpenAI client."""
        if self._openai_client is None:
            from os import getenv
            self._openai_client = AsyncOpenAI(api_key=getenv("OPENAI_API_KEY"))
        return self._openai_client

    def _render_page_to_base64(self, page: fitz.Page) -> str:
        """Render a PDF page to a base64-encoded PNG image."""
        pix = page.get_pixmap(dpi=self.dpi)
        png_bytes = pix.tobytes("png")
        return base64.b64encode(png_bytes).decode("utf-8")

    async def _analyze_slide_image(self, base64_image: str, page_num: int) -> dict | None:
        """Analyze slide image using GPT-4o Vision."""
        client = self._get_openai()
        for attempt in range(2):
            try:
                response = await client.responses.create(
                    model=VISION_MODEL,
                    input=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": VISION_PROMPT},
                                {
                                    "type": "input_image",
                                    "image_url": f"data:image/png;base64,{base64_image}",
                                },
                            ],
                        }
                    ],
                )

                # Try to extract JSON from response
                response_text = response.output_text
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    return json.loads(json_match.group())
                return json.loads(response_text.strip())

            except json.JSONDecodeError as e:
                print(f"    Warning: Could not parse JSON for page {page_num}: {e}")
                return None
            except Exception as e:
                if attempt == 0:
                    await asyncio.sleep(1)
                    continue
                print(f"    Warning: Vision analysis failed for page {page_num}: {e}")
                return None

    def _extract_text_from_analysis(self, analysis: dict | None) -> str:
        """Extract readable text from analysis for embedding."""
        if not analysis:
            return ""

        text_parts = []

        if "slide_title" in analysis and analysis["slide_title"]:
            text_parts.append(analysis["slide_title"])

        if "key_points" in analysis and isinstance(analysis["key_points"], list):
            for point in analysis["key_points"]:
                if isinstance(point, str):
                    text_parts.append(point)

        if analysis.get("raw_text"):
            text_parts.append(analysis["raw_text"])

        return "\n".join(text_parts)

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

        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            total_pages = len(doc)
            print(f"Found {total_pages} pages")
            reader = PdfReader(io.BytesIO(pdf_bytes))

            for page_num, page in enumerate(doc, start=1):
                start_time = time.time()
                print(f"  Processing Page {page_num}/{total_pages}...", end=" ", flush=True)

                # Render page to image
                base64_image = self._render_page_to_base64(page)

                # Analyze with vision
                analysis = await self._analyze_slide_image(base64_image, page_num)
                text = self._extract_text_from_analysis(analysis)

                # If vision returned nothing useful, try raw text extraction
                if not text.strip() or len(text.strip()) < 20:
                    if page_num - 1 < len(reader.pages):
                        raw_text = reader.pages[page_num - 1].extract_text() or ""
                        if raw_text.strip():
                            vision_text = text.strip()
                            fallback_text = raw_text.strip()
                            text = (
                                f"{vision_text}\n{fallback_text}"
                                if vision_text and fallback_text not in vision_text
                                else fallback_text
                            )

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
        description="Process PDF slides using GPT-4o Vision and create embeddings"
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
    parser.add_argument(
        "--dpi",
        type=int,
        default=RENDER_DPI,
        help=f"DPI for rendering pages (default: {RENDER_DPI})"
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
        processor = SlideProcessor(dpi=args.dpi)
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
