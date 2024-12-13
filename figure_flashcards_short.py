import os
import re
import fitz  # PyMuPDF for PDF handling
from PIL import Image
import numpy as np
from groq import Groq  # Assuming you have a Groq client library

# Constants
LLM_MODEL = "llama3-8b-8192"  # Replace with the LLM model name
MEDIA_FOLDER = "anki_media"  # Local folder for Anki media
TSV_FILE = "flashcards.tsv"  # Flashcards TSV file
CHUNK_SIZE = 2500

# Define the prompt for refining captions
CAPTION_PROMPT = """
You are tasked with creating the front of a flashcard from a provided caption or description of a figure. Use the following strict format and instructions:

### BEGIN FLASHCARD ###
Prompt: [Refine the caption into a clear and concise question or description suitable for the front of a flashcard. The prompt should provide enough context for the learner to recall the figure or concept. Avoid generic or vague phrases. Ensure the prompt is concise but specific.]
### END FLASHCARD ###

Guidelines:
- Include key details from the caption that are necessary for understanding the figure or concept.
- Do not include any additional explanations, footnotes, or irrelevant information outside the specified format.
- Ensure clarity and conciseness in the flashcard prompt.
- Avoid any redundancy or overcomplication.
- Focus on turning the caption into an engaging and meaningful question or description that can serve as the front of a flashcard.

Provide the refined flashcard prompt in the exact format described above. Do not include explanations or justifications for your output.
"""

def ensure_directory(path):
    """Ensure a directory exists."""
    if not os.path.exists(path):
        os.makedirs(path)

# LLM Client Initialization
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Helper Functions
def extract_captions_from_text(page_text, max_words=25):
    """Extract captions for labeled figures like 'Figure 2.1'."""
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
    """Detect the white margin in an image to crop dynamically."""
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
    """Refine captions using LLM."""
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
    """Extract figures and captions from the PDF."""
    pdf_document = fitz.open(pdf_path)
    ensure_directory(MEDIA_FOLDER)
    flashcards = []
    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        print(f"Processing Page {page_num + 1}...")
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
                        image_filename = f"page_{page_num + 1}_figure.png"
                        image_path = os.path.join(MEDIA_FOLDER, image_filename)
                        pix.save(image_path)

                        caption = next((cap[1] for cap in captions if cap[0] in span["text"]), "None")
                        refined_caption = process_caption_with_llm(caption)

                        flashcards.append((refined_caption, f"<img src=\"{image_filename}\">"))
    pdf_document.close()
    return flashcards

def save_flashcards_to_tsv(flashcards):
    """Save flashcards to a TSV file."""
    with open(TSV_FILE, "w") as tsv_file:
        for front, back in flashcards:
            tsv_file.write(f"{front}\t{back}\n")

# Main Execution
pdf_file = "practice_text.pdf"  # Replace with your PDF file name
print("Extracting figures and captions...")
flashcards = extract_figures_with_captions(pdf_file)
print(f"Saving flashcards to {TSV_FILE}...")
save_flashcards_to_tsv(flashcards)
print("Flashcards created successfully! Make sure to move the images to Anki's media folder.")

