import ollama
import fitz  # PyMuPDF
import json
import time
import os
from pathlib import Path

# Configuration
SLIDES_DIR = "slides"
OUTPUT_DIR = "sources"
MODEL = "gemma3:4b"

# The Prompt
PROMPT_TEXT = """
I want key points and topics from each slide in this slide deck. 
Prefer information especially around AI, Machine Learning, the future of work, and news or updates about Birmingham AI.
Include only pages with content. Do not include empty pages. 
Give them to me as JSON with each key point and topic broken into a separate record.
Ensure that the JSON is valid and well-formed.
The JSON should have "page", "file_name", "slide_title", and "slide_analysis" fields.
The file_name should be the name of the uploaded file.
The page should be the page number of the slide.
The slide_title should be the title of the slide.
The slide_analysis should be an array of objects with the following fields:
    "key_point": the text of the key point or topic.
"""

def process_slides(pdf_path):
    """Process a single PDF file and extract key points from slides."""
    # Generate output path
    pdf_filename = os.path.basename(pdf_path)
    json_filename = pdf_filename.replace(".pdf", ".json")
    json_path = os.path.join(OUTPUT_DIR, json_filename)
    
    # Open the PDF using context manager to ensure proper cleanup
    try:
        with fitz.open(pdf_path) as doc:
            all_slides_data = []

            # Iterate through pages
            for page_num, page in enumerate(doc, start=1):
                start_time = time.time()
                
                # Extract text
                text = page.get_text()
                
                # Skip empty pages
                if not text.strip():
                    print(f"  Skipping Page {page_num} (Empty)")
                    continue

                print(f"  Processing Page {page_num}...", end=" ", flush=True)

                # Call Ollama
                response = ollama.chat(
                    model=MODEL,
                    format='json',  # Enforce JSON mode
                    messages=[
                        {
                            'role': 'system',
                            'content': "You are a helper that analyzes slide text and outputs strict JSON."
                        },
                        {
                            'role': 'user',
                            'content': f"{PROMPT_TEXT}\n\nFILE NAME: {pdf_filename}\n\nCONTEXT:\n{text}"
                        },
                    ]
                )

                # Parse JSON content
                try:
                    content = json.loads(response['message']['content'])
                    
                    # Add metadata
                    slide_result = {
                        "page": page_num,
                        "analysis": content
                    }
                    all_slides_data.append(slide_result)
                    
                    elapsed = time.time() - start_time
                    print(f"Done ({elapsed:.2f}s)")

                except json.JSONDecodeError:
                    print(f"Failed to parse JSON for page {page_num}")

            # Save complete results to a file
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(all_slides_data, f, indent=2)
            
            print(f"  Saved analysis for {len(all_slides_data)} slides to '{json_path}'")
            return len(all_slides_data)
    except Exception as e:
        print(f"Error opening PDF {pdf_path}: {e}")
        return 0

def main():
    """Main function to process all PDFs in the slides directory."""
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Get all PDF files from slides directory
    slides_path = Path(SLIDES_DIR)
    if not slides_path.exists():
        print(f"Error: Slides directory '{SLIDES_DIR}' not found!")
        return
    
    pdf_files = list(slides_path.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in '{SLIDES_DIR}' directory!")
        return
    
    print(f"Found {len(pdf_files)} PDF file(s) to process\n")
    
    # PRO TIP: Warm up the model once before processing all PDFs
    # We send an empty request to force Ollama to load the model into VRAM 
    # before we start the loop. This makes the first slide processing instant.
    print(f"Warming up {MODEL}...")
    ollama.generate(model=MODEL, prompt="") 
    print("Model loaded. Starting processing...\n")
    
    total_slides = 0
    
    # Process each PDF
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] Processing: {pdf_path.name}")
        slides_count = process_slides(str(pdf_path))
        total_slides += slides_count
        print()
    
    print(f"All done! Processed {len(pdf_files)} PDF(s) with {total_slides} total slides.")

if __name__ == "__main__":
    main()