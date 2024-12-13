import os
import re
import fitz  # PyMuPDF for figures
import PyPDF2  # For PDF text extraction
import argparse
import time
from PIL import Image
import numpy as np
from groq import Groq  # Assuming you have a Groq client library

# Constants
CHUNK_SIZE = 2700  # Approximate token limit for text chunks
MAX_CAPTION_WORDS = 25  # Maximum words to extract for figure captions
FLASHCARD_OUTPUT = "flashcards.txt"

# Initialize Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# LLM Prompt
KEYWORD_PROMPT = """
You are tasked with extracting structured information from the provided text. For each keyword or concept, provide the following in a consistent format:

1. **Term**: The key term or concept.
2. **Definition**: A concise and clear definition of the term or concept.
3. **Example**: Provide one relevant example that illustrates the term. If no example is explicitly available, return "None".

Format the output exactly like this (including all symbols and delimiters):

### BEGIN ENTRY ###
Term: [Term]
Definition: [Definition]
Example: [Example]
### END ENTRY ###

Ensure the following:
- Each entry is enclosed between "### BEGIN ENTRY ###" and "### END ENTRY ###".
- Use precise, concise language.
- Exclude any unrelated or random words or content.
- Ignore redundant terms or repeated examples.
- If the provided text lacks a term, definition, or example, explicitly write "None" for that part.
- Ensure the output is ready to be concatenated with outputs from other chunks without ambiguity.

Only provide the requested structured output in the exact format described. Do not include explanations or introductions.
"""


# --- Helper Functions ---
def extract_text_from_pdf(pdf_path):
    """Extracts text from a given PDF file."""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text


def find_theorem_or_definition_starts(text):
    """Identifies section starts based on 'Theorem' or 'Definition' followed by a number."""
    pattern = r"\b(Theorem|Definition)\s\d+\.\d+(\.\d+)?\b"
    matches = [(m.start(), m.group()) for m in re.finditer(pattern, text)]
    return matches


def split_large_section(section, chunk_size):
    """Splits a large section into smaller chunks respecting paragraph breaks."""
    chunks = []
    while len(section) > chunk_size:
        split_point = section[:chunk_size].rfind("\n\n")  # Split at the last paragraph break
        if split_point == -1:
            split_point = chunk_size  # If no paragraph break, split arbitrarily
        chunks.append(section[:split_point].strip())
        section = section[split_point:].strip()
    if section:
        chunks.append(section)
    return chunks


def chunk_text_by_theorem_definition(text, section_starts, chunk_size=CHUNK_SIZE):
    """Splits the text into chunks based on 'Theorem' or 'Definition' followed by a number."""
    chunks = []

    for i, (start, marker) in enumerate(section_starts):
        end = section_starts[i + 1][0] if i + 1 < len(section_starts) else len(text)
        section = text[start:end].strip()

        # Check if the section needs further splitting
        if len(section) > chunk_size:
            chunks.extend(split_large_section(section, chunk_size))
        else:
            chunks.append(section)

    return chunks


def extract_captions_from_text(page_text):
    """Extract captions for labeled figures like 'Figure 2.1'."""
    pattern = r"(Figure\s\d+\.\d+(\.\d+)?)"
    matches = re.finditer(pattern, page_text)

    captions = []

    for match in matches:
        figure_label = match.group(0)
        start_index = match.end()
        remaining_text = page_text[start_index:].strip()

        # Extract up to MAX_CAPTION_WORDS or until the next period
        words = remaining_text.split()
        caption = " ".join(words[:MAX_CAPTION_WORDS])
        captions.append((figure_label, caption))

    return captions


def extract_figures_with_captions(pdf_path, output_folder):
    """Extract figures and their captions from a PDF."""
    os.makedirs(output_folder, exist_ok=True)
    pdf_document = fitz.open(pdf_path)
    flashcards = []

    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        print(f"Processing Page {page_num + 1}...")

        # Extract raw text for captions
        page_text = page.get_text("text")
        captions = extract_captions_from_text(page_text)

        text_dict = page.get_text("dict")
        for block in text_dict["blocks"]:
            if "lines" not in block:
                continue

            for line in block["lines"]:
                for span in line["spans"]:
                    if "Figure" in span["text"] and span["size"] > 10:
                        x0, y0, x1, y1 = span["bbox"]
                        cropped_area = fitz.Rect(x0 - 25, y0 - 10, x1 + 350, y1 + 500)
                        pix = page.get_pixmap(clip=cropped_area)

                        # Save the figure
                        figure_path = os.path.join(output_folder, f"page_{page_num + 1}_figure.png")
                        pix.save(figure_path)
                        print(f"Extracted figure to {figure_path}")

                        # Find the corresponding caption
                        caption = next((cap[1] for cap in captions if cap[0] in span["text"]), None)

                        # Save as flashcard
                        flashcards.append((figure_path, caption))

    pdf_document.close()
    return flashcards


def generate_flashcards_with_llm(chunks):
    """Generate flashcards for text chunks using an LLM."""
    flashcards = []

    for i, chunk in enumerate(chunks, start=1):
        print(f"Processing chunk {i}/{len(chunks)}...")

        # Send chunk to LLM
        response = client.chat.completions.create(
            messages=[
                {'role': 'system', 'content': KEYWORD_PROMPT},
                {'role': 'user', 'content': chunk}
            ],
            model="llama3-8b-8192",
        )

        output = response.choices[0].message.content
        flashcards.append(output)

        # Delay to avoid rate limits
        time.sleep(10)

    return flashcards


def create_flashcards(pdf_path, output_folder):
    """Generate flashcards from both text chunks and figure captions."""
    text = extract_text_from_pdf(pdf_path)

    # Process text chunks
    section_starts = find_theorem_or_definition_starts(text)
    chunks = chunk_text_by_theorem_definition(text, section_starts)

    # Generate flashcards for text chunks using LLM
    chunk_flashcards = generate_flashcards_with_llm(chunks)

    # Create flashcards for figures
    figure_flashcards = extract_figures_with_captions(pdf_path, output_folder)

    # Combine flashcards
    all_flashcards = chunk_flashcards + [
        (figure[1], figure[0]) for figure in figure_flashcards
    ]

    # Save flashcards to a file
    with open(FLASHCARD_OUTPUT, "w") as f:
        for front, back in all_flashcards:
            f.write(f"Front: {front}\nBack: {back}\n{'-' * 50}\n")

    print(f"Flashcards saved to {FLASHCARD_OUTPUT}")

def create_flashcards_limited(pdf_path, output_folder, max_chunks=5):
    """Generate flashcards from the first few chunks and print them."""
    text = extract_text_from_pdf(pdf_path)

    # Process text chunks
    section_starts = find_theorem_or_definition_starts(text)
    chunks = chunk_text_by_theorem_definition(text, section_starts)

    # Limit to the first `max_chunks` chunks
    limited_chunks = chunks[:max_chunks]

    # Generate flashcards for limited chunks using LLM
    chunk_flashcards = generate_flashcards_with_llm(limited_chunks)

    # Create flashcards for figures
    figure_flashcards = extract_figures_with_captions(pdf_path, output_folder)

    # Combine flashcards
    all_flashcards = chunk_flashcards + [
        (figure[1], figure[0]) for figure in figure_flashcards
    ]

    # Debug: Print all_flashcards before processing
    print("All flashcards content before processing:", all_flashcards)

    # Print flashcards to the console
    for front, back in all_flashcards:
        print(f"Front: {front}\nBack: {back}\n{'-' * 50}")

    print("\nProcessing completed for the first 5 chunks.")


# --- Main Execution ---
pdf_file = "practice_text.pdf"
output_dir = "output_figures"

create_flashcards_limited(pdf_file, output_dir, max_chunks=5)
