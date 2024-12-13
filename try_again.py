import os
import re
import time
import fitz  # PyMuPDF for PDF handling
import PyPDF2  # For PDF text extraction
from PIL import Image
import numpy as np
from groq import Groq  # Assuming you have a Groq client library

# Constants
CHUNK_SIZE = 2700  # Token limit for text chunks
MEDIA_FOLDER = "anki_media"  # Local folder for Anki media
TSV_FILE = "flashcards.tsv"  # Final flashcards TSV file
LLM_MODEL = "llama3-8b-8192"

# LLM Prompts
KEYWORD_PROMPT = """
You are tasked with extracting structured information from the provided text. For each keyword or concept, provide the following in a consistent format:

1. **Term**: The key term or concept.
2. **Definition**: A concise and clear definition of the term or concept. Include relevant details or examples if explicitly available in the text.

Format the output exactly like this (including all symbols and delimiters):

### BEGIN ENTRY ###
Term: [Term]
Definition: [Definition]
### END ENTRY ###

Ensure the following:
- Each entry is enclosed between "### BEGIN ENTRY ###" and "### END ENTRY ###".
- Use precise, concise language.
- Exclude any unrelated or random words or content.
- Ignore redundant terms or repeated examples.
"""

CAPTION_PROMPT = """
You are tasked with analyzing a provided caption for a figure and creating the front of a flashcard. Your goal is to interpret what the figure generally represents based on the caption and generate a meaningful, concise question or description for the front of the flashcard. Use the following strict format and instructions:

### BEGIN FLASHCARD ###
Prompt: [Write a general question or description suitable for the front of a flashcard.]
### END FLASHCARD ###
"""

# Initialize Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Helper Functions
def ensure_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)

def extract_text_from_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text

def chunk_text(text, chunk_size=CHUNK_SIZE):
    chunks = []
    while len(text) > chunk_size:
        split_point = text[:chunk_size].rfind("\n\n")
        if split_point == -1:
            split_point = chunk_size
        chunks.append(text[:split_point].strip())
        text = text[split_point:].strip()
    if text:
        chunks.append(text)
    return chunks

def generate_flashcards_with_llm(chunks):
    flashcards = []
    for i, chunk in enumerate(chunks, start=1):
        print(f"Processing chunk {i}/{len(chunks)}...")
        response = client.chat.completions.create(
            messages=[
                {'role': 'system', 'content': KEYWORD_PROMPT},
                {'role': 'user', 'content': chunk}
            ],
            model=LLM_MODEL,
        )
        flashcards.append(response.choices[0].message.content)
        time.sleep(10)
    return flashcards

def parse_llm_output(output):
    flashcards = []
    entries = re.findall(r"### BEGIN ENTRY ###(.*?)### END ENTRY ###", output, re.DOTALL)
    for entry in entries:
        term_match = re.search(r"Term: (.*?)\n", entry)
        definition_match = re.search(r"Definition: (.*?)\n", entry)
        term = term_match.group(1).strip() if term_match else "Unknown Term"
        definition = definition_match.group(1).strip() if definition_match else "No definition available."
        flashcards.append((term, definition))
    return flashcards

def extract_figures_with_captions(pdf_path):
    pdf_document = fitz.open(pdf_path)
    ensure_directory(MEDIA_FOLDER)
    flashcards = []
    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        page_text = page.get_text("text")
        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    if "Figure" in span["text"]:
                        x0, y0, x1, y1 = span["bbox"]
                        cropped_area = fitz.Rect(x0, y0, x1 + 350, y1 + 500)
                        pix = page.get_pixmap(clip=cropped_area)
                        temp_image_path = os.path.join(MEDIA_FOLDER, f"page_{page_num + 1}_figure.png")
                        pix.save(temp_image_path)
                        flashcards.append((span["text"], f"<img src=\"{temp_image_path}\">"))
    pdf_document.close()
    return flashcards

def save_flashcards_to_tsv(flashcards):
    with open(TSV_FILE, "w") as tsv_file:
        for front, back in flashcards:
            tsv_file.write(f"{front}\t{back}\n")

# Main Execution
if __name__ == "__main__":
    pdf_file = input("Enter the path to the PDF file: ")

    print("Extracting text-based flashcards...")
    text = extract_text_from_pdf(pdf_file)
    chunks = chunk_text(text)
    raw_text_flashcards = generate_flashcards_with_llm(chunks)
    text_flashcards = []
    for raw_output in raw_text_flashcards:
        text_flashcards.extend(parse_llm_output(raw_output))

    print("Extracting figure-based flashcards...")
    figure_flashcards = extract_figures_with_captions(pdf_file)

    all_flashcards = text_flashcards + figure_flashcards
    save_flashcards_to_tsv(all_flashcards)

    print(f"All flashcards saved to {TSV_FILE}. Ensure media files are moved to Anki's media folder.")

