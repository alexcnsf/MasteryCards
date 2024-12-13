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
TSV_FILE = "flashcards.tsv"  # Flashcards TSV file
CHUNK_SIZE = 2500

# Prompts
CAPTION_PROMPT = """
You are tasked with analyzing a provided caption for a figure and creating the front of a flashcard. Your goal is to interpret what the figure generally represents based on the caption and generate a meaningful, concise question or description for the front of the flashcard. Use the following strict format and instructions:

### BEGIN FLASHCARD ###
Prompt: [Write a general question or description suitable for the front of a flashcard. The prompt should focus on the broader concept or idea represented by the figure, rather than overly specific details. Ensure the prompt provides enough context for a learner to understand the figure's purpose.]
### END FLASHCARD ###
"""

# Initialize Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Ensure directory exists
def ensure_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)

# Save image to file
def save_image(image, file_name):
    image_path = os.path.join(MEDIA_FOLDER, file_name)
    image.save(image_path, "PNG")
    return file_name

# Extract and save figure images
def extract_images_from_page(page, caption_label):
    image_list = []
    for img_index, img in enumerate(page.get_images(full=True), start=1):
        xref = img[0]
        base_image = page.get_pixmap(xref)
        pil_image = Image.frombytes("RGB", [base_image.width, base_image.height], base_image.samples)
        file_name = f"{caption_label.replace(' ', '_')}_image_{img_index}.png"
        save_image(pil_image, file_name)
        image_list.append(file_name)
    return image_list

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

# Process caption with LLM
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

# Extract figures and captions
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
            images = extract_images_from_page(page, caption[0])
            image_placeholder = ", ".join(images) if images else "No image available"
            flashcards.append((refined_caption, image_placeholder))
    pdf_document.close()
    return flashcards

# Save flashcards to TSV
def save_flashcards_to_tsv(flashcards):
    with open(TSV_FILE, "a") as tsv_file:
        for front, back in flashcards:
            tsv_file.write(f"{front}\t{back}\n")

# Main Execution
pdf_file = input("Enter the PDF file name (with extension): ").strip()

# Process captions from figures
figure_flashcards = extract_figures_with_captions(pdf_file)
save_flashcards_to_tsv(figure_flashcards)

print("All flashcards have been successfully saved to the TSV file!")

