import os
import re
import time
import fitz  # PyMuPDF for PDF handling
from PIL import Image
import numpy as np
import PyPDF2  # For PDF text extraction
from groq import Groq  # Assuming you have a Groq client library
from collections import OrderedDict

# Constants
LLM_MODEL = "llama3-8b-8192"  # Replace with the LLM model name
MEDIA_FOLDER = "anki_media"  # Local folder for Anki media
TSV_FILE = "flashcards.tsv"  # Flashcards TSV file
CHUNK_SIZE = 2500
FLASHCARD_REDUCTION_RATIO = 0.2  # Only keep 20% of the generated flashcards

# Prompts
CAPTION_PROMPT = """
You are tasked with analyzing a provided caption for a figure and creating the front of a flashcard. Your goal is to interpret what the figure generally represents based on the caption and generate a meaningful, concise question or description for the front of the flashcard. Use the following strict format and instructions:

### BEGIN FLASHCARD ###
Prompt: [Write a general question or description suitable for the front of a flashcard. The prompt should focus on the broader concept or idea represented by the figure, rather than overly specific details. Ensure the prompt provides enough context for a learner to understand the figure's purpose.]
### END FLASHCARD ###

"""

KEYWORD_PROMPT = """
You are tasked with extracting structured information from the provided text. For the most important single  keyword or concept, provide the following in a consistent format:

1. **Term**: The key term or concept.
2. **Definition**: A concise and clear definition of the term or concept.

Format the output exactly like this (including all symbols and delimiters):

### BEGIN ENTRY ###
Term: [Term]
Definition: [Definition]
### END ENTRY ###

Guidelines:
- Generate no more than **two flashcards** per chunk.
- Select the most important and unique concepts or terms in the chunk.
- Avoid repetition or overlapping terms within the chunk output.
- Exclude redundant or overly technical definitions without sufficient explanation.
"""

DEDUPLICATION_PROMPT = """
You are tasked with reviewing a complete list of flashcards and removing any duplicates, overlaps, or redundancies to ensure only unique and valuable flashcards remain. Follow these instructions:

1. Carefully analyze all provided flashcards for duplicate topics, terms, or overlapping definitions.
2. Retain only one flashcard per unique topic or concept. The retained flashcard should be the most concise, clear, and informative version.
3. Select a reduced set of flashcards, keeping only the top 20% of the most diverse and informative entries.
4. Ensure the final selection of flashcards provides a comprehensive yet concise set of key terms and ideas.

Your output should strictly follow this format:

### BEGIN FINAL SELECTION ###
Selected Indices: [List of numbers separated by commas, e.g., 1, 3, 5, 7]
### END FINAL SELECTION ###

Do not include any additional comments, explanations, or output beyond the specified format.
"""

# Initialize Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Ensure directory exists
def ensure_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)

# PDF Caption Extraction
def extract_captions_from_text(page_text, max_words=25):
    pattern = r"(Figure\s\d+\.\d+(\.\d+)?)"
    matches = re.finditer(pattern, page_text)
    captions = []
    for match in matches:
        figure_label = match.group(0)
        start_index = match.end()
        remaining_text = page_text[start_index:].strip()
        words = remaining_text.split()
        caption = " ".join(words[:max_words])
        captions.append((figure_label, caption))
    return captions

def process_caption_with_llm(caption):
    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": CAPTION_PROMPT},
            {"role": "user", "content": f"Refine this caption: {caption}"}
        ],
        model=LLM_MODEL
    )
    refined_caption = response.choices[0].message.content.strip()
    match = re.search(r"### BEGIN FLASHCARD ###\nPrompt: (.*?)\n### END FLASHCARD ###", refined_caption, re.DOTALL)
    return match.group(1).strip() if match else "Error in LLM response"

def extract_figures_with_captions(pdf_path):
    pdf_document = fitz.open(pdf_path)
    ensure_directory(MEDIA_FOLDER)
    flashcards = []
    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        page_text = page.get_text("text")
        captions = extract_captions_from_text(page_text)
        for caption in captions:
            refined_caption = process_caption_with_llm(caption[1])
            flashcards.append((refined_caption, "Image placeholder"))
    pdf_document.close()
    return flashcards

# PDF Text Extraction
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
        response = client.chat.completions.create(
            messages=[
                {'role': 'system', 'content': KEYWORD_PROMPT},
                {'role': 'user', 'content': chunk}
            ],
            model=LLM_MODEL
        )
        output = response.choices[0].message.content
        entries = re.findall(r"### BEGIN ENTRY ###(.*?)### END ENTRY ###", output, re.DOTALL)
        for entry in entries:
            term_match = re.search(r"Term: (.*?)\n", entry)
            definition_match = re.search(r"Definition: (.*?)\n", entry)

            term = term_match.group(1).strip() if term_match else "Unknown Term"
            definition = definition_match.group(1).strip() if definition_match else "No definition available."

            flashcards.append((term, definition))
    return flashcards

def deduplicate_flashcards(flashcards):
    # Remove duplicates based on the front of the flashcard
    unique_flashcards = list(OrderedDict((fc[0].strip().lower(), fc) for fc in flashcards).values())

    # Limit flashcards to 20% of original size
    num_to_keep = max(1, int(len(unique_flashcards) * FLASHCARD_REDUCTION_RATIO))
    reduced_flashcards = unique_flashcards[:num_to_keep]

    return reduced_flashcards

# Save flashcards to TSV
def save_flashcards_to_tsv(flashcards):
    with open(TSV_FILE, "w") as tsv_file:  # Overwrite to ensure only final set is saved
        for front, back in flashcards:
            tsv_file.write(f"{front}\t{back}\n")

# Main Execution
pdf_file = input("Enter the name of the PDF file (e.g., practice_text.pdf): ")

# Process captions from figures
figure_flashcards = extract_figures_with_captions(pdf_file)

# Process keywords and concepts from text
text = extract_text_from_pdf(pdf_file)
chunks = chunk_text(text)
chunk_flashcards = generate_flashcards_with_llm(chunks)

# Combine and deduplicate flashcards
total_flashcards = figure_flashcards + chunk_flashcards
#deduplicated_flashcards = deduplicate_flashcards(total_flashcards)

# Save reduced and deduplicated flashcards to TSV
save_flashcards_to_tsv(total_flashcards)

print("All flashcards have been successfully saved to the TSV file!")

