import os
import re
import time
import fitz  # PyMuPDF for PDF handling
from PIL import Image
import numpy as np
import PyPDF2  # For PDF text extraction
from groq import Groq  # Assuming you have a Groq client library

# Constants
LLM_MODEL = "llama3-8b-8192"  # Replace with the LLM model name
MEDIA_FOLDER = "anki_media"  # Local folder for Anki media
TSV_FILE = "flashcards.tsv"  # Combined Flashcards TSV file
CHUNK_SIZE = 2500

# Define prompts
CAPTION_PROMPT = """
You are tasked with analyzing a provided caption for a figure and creating the front of a flashcard. Your goal is to interpret what the figure generally represents based on the caption and generate a meaningful, concise question or description for the front of the flashcard. Use the following strict format and instructions:

### BEGIN FLASHCARD ###
Prompt: [Write a general question or description suitable for the front of a flashcard. The prompt should focus on the broader concept or idea represented by the figure, rather than overly specific details. Ensure the prompt provides enough context for a learner to understand the figure's purpose.]
### END FLASHCARD ###
"""

KEYWORD_PROMPT = """
You are tasked with extracting structured information from the provided text. For each keyword or concept, provide the following in a consistent format:

1. **Term**: The key term or concept.
2. **Definition**: A concise and clear definition of the term or concept. Include relevant details or examples if explicitly available in the text.

### BEGIN ENTRY ###
Term: [Term]
Definition: [Definition]
### END ENTRY ###
"""

# Initialize Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Helper functions
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

def extract_captions_from_text(page_text, max_words=50):
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

def detect_white_margin(image_path, tolerance=250, min_consecutive_white=15):
    image = Image.open(image_path)
    image_array = np.array(image)
    height, width, _ = image_array.shape
    consecutive_white_rows = 0
    for y in range(height):
        row = image_array[y, :, :]
        if np.all(row >= tolerance):
            consecutive_white_rows += 1
            if consecutive_white_rows >= min_consecutive_white:
                return y
        else:
            consecutive_white_rows = 0
    return height

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

def generate_flashcards_with_llm(chunks):
    flashcards = []
    for i, chunk in enumerate(chunks, start=1):
        print(f"Processing text chunk {i}/{len(chunks)}...")
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": KEYWORD_PROMPT},
                {"role": "user", "content": chunk}
            ],
            model=LLM_MODEL
        )
        output = response.choices[0].message.content
        flashcards.extend(parse_llm_output(output))
        time.sleep(10)  # Delay to avoid rate limits
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
        print(f"Processing page {page_num + 1}...")
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
                        temp_image_path = os.path.join(MEDIA_FOLDER, "temp_image.png")
                        pix.save(temp_image_path)
                        new_bottom = detect_white_margin(temp_image_path)
                        final_cropped_area = fitz.Rect(x0 - 25, y0 - 10, x1 + 350, y0 + new_bottom)
                        final_pix = page.get_pixmap(clip=final_cropped_area)
                        image_filename = f"page_{page_num + 1}_figure.png"
                        image_path = os.path.join(MEDIA_FOLDER, image_filename)
                        final_pix.save(image_path)
                        caption = next((cap[1] for cap in captions if cap[0] in span["text"]), "None")
                        refined_caption = process_caption_with_llm(caption)
                        flashcards.append((refined_caption, f"<img src=\"{image_filename}\">"))
    pdf_document.close()
    return flashcards

def save_flashcards_to_tsv(flashcards):
    with open(TSV_FILE, "w") as tsv_file:
        for front, back in flashcards:
            tsv_file.write(f"{front}\t{back}\n")

# Main Execution
if __name__ == "__main__":
    pdf_file = input("Enter the path to the PDF file: ").strip()
    ensure_directory(MEDIA_FOLDER)

    print("Extracting text-based flashcards...")
    text = extract_text_from_pdf(pdf_file)
    chunks = chunk_text(text)
    text_flashcards = generate_flashcards_with_llm(chunks)

    print("Extracting figure-based flashcards...")
    figure_flashcards = extract_figures_with_captions(pdf_file)

    all_flashcards = text_flashcards + figure_flashcards

    print(f"Saving all flashcards to {TSV_FILE}...")
    save_flashcards_to_tsv(all_flashcards)

    print("Flashcards created successfully! Make sure to move the images to Anki's media folder.")

