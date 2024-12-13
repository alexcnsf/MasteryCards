import os
import re
import time
import fitz  # PyMuPDF for PDF handling
from PIL import Image
import numpy as np
import PyPDF2  # For PDF text extraction
from groq import Groq  # Assuming you have a Groq client library
import shutil
import platform

# Constants
CHUNK_SIZE = 2700  # Approximate token limit for text chunks
ANKI_OUTPUT = "flashcards.tsv"
MEDIA_FOLDER = "anki_media"  # Local folder for Anki media
LLM_MODEL = "llama3-8b-8192"  # Replace with the LLM model name

# Initialize Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

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
- If the provided text lacks a term or definition, explicitly write "None" for that part.
- Ensure the output is ready to be concatenated with outputs from other chunks without ambiguity.

Only provide the requested structured output in the exact format described. Do not include explanations or introductions.
"""

CAPTION_PROMPT = """
You are tasked with analyzing a provided caption for a figure and creating the front of a flashcard. Your goal is to interpret what the figure generally represents based on the caption and generate a meaningful, concise question or description for the front of the flashcard. Use the following strict format and instructions:

### BEGIN FLASHCARD ###
Prompt: [Write a general question or description suitable for the front of a flashcard. The prompt should focus on the broader concept or idea represented by the figure, rather than overly specific details. Ensure the prompt provides enough context for a learner to understand the figure's purpose.]
### END FLASHCARD ###

Guidelines:
- Emphasize the general idea or purpose of the figure.
- Avoid using overly specific or technical phrases unless necessary.
- Ensure clarity and conciseness in the flashcard prompt.
- Do not include any additional explanations, footnotes, or irrelevant information outside the specified format.
- If the caption lacks sufficient context, infer a broader interpretation of what the figure might represent.

Provide the refined flashcard prompt in the exact format described above. Do not include explanations or justifications for your output.
"""

# Helper Functions
def ensure_directory(path):
    """Ensure a directory exists."""
    if not os.path.exists(path):
        os.makedirs(path)

def extract_text_from_pdf(pdf_path):
    """Extracts text from a given PDF file."""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text

def chunk_text(text, chunk_size=CHUNK_SIZE):
    """Splits text into chunks of a specified size."""
    chunks = []
    while len(text) > chunk_size:
        split_point = text[:chunk_size].rfind("\n\n")  # Split at the last paragraph break
        if split_point == -1:
            split_point = chunk_size  # If no paragraph break, split arbitrarily
        chunks.append(text[:split_point].strip())
        text = text[split_point:].strip()
    if text:
        chunks.append(text)
    return chunks

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
            model=LLM_MODEL,
        )

        output = response.choices[0].message.content
        flashcards.append(output)

        # Delay to avoid rate limits
        time.sleep(10)

    return flashcards

def parse_llm_output(output):
    """Parses LLM output into a list of (front, back) flashcards."""
    flashcards = []
    entries = re.findall(r"### BEGIN ENTRY ###(.*?)### END ENTRY ###", output, re.DOTALL)

    for entry in entries:
        term_match = re.search(r"Term: (.*?)\n", entry)
        definition_match = re.search(r"Definition: (.*?)\n", entry)

        term = term_match.group(1).strip() if term_match else "Unknown Term"
        definition = definition_match.group(1).strip() if definition_match else "No definition available."

        flashcards.append((term, definition))

    return flashcards

def extract_captions_from_text(page_text, max_words=50):
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
                        is_bold = "Bold" in span["font"] or "Black" in span["font"]
                        x0, y0, x1, y1 = span["bbox"]

                        if is_bold and x0 < 50:  # Left margin condition
                            print(f"Found bold 'Figure' in left margin on page {page_num + 1}")

                            # Temporary large crop area
                            cropped_area = fitz.Rect(x0 - 25, y0 - 10, x1 + 350, y1 + 500)
                            pix = page.get_pixmap(clip=cropped_area)

                            # Save initial large image
                            temp_image_path = os.path.join(MEDIA_FOLDER, "temp_image.png")
                            pix.save(temp_image_path)

                            # Detect white margin
                            new_bottom = detect_white_margin(temp_image_path)
                            final_cropped_area = fitz.Rect(x0 - 25, y0 - 10, x1 + 350, y0 + new_bottom)

                            # Render the final cropped area
                            final_pix = page.get_pixmap(clip=final_cropped_area)
                            image_filename = f"page_{page_num + 1}_figure.png"
                            image_path = os.path.join(MEDIA_FOLDER, image_filename)
                            final_pix.save(image_path)

                            # Find the corresponding caption
                            caption = next((cap[1] for cap in captions if cap[0] in span["text"]), "None")
                            refined_caption = process_caption_with_llm(caption)

                            flashcards.append((refined_caption, f"<img src=\"{image_filename}\">"))
    pdf_document.close()
    return flashcards

def save_flashcards_to_tsv(flashcards):
    """Save flashcards to a TSV file."""
    with open(ANKI_OUTPUT, "w") as tsv_file:
        for front, back in flashcards:
            tsv_file.write(f"{front}\t{back}\n")

def create_combined_flashcards(pdf_path, max_chunks=3):
    """Generate flashcards from both text chunks and figures."""
    print("Extracting text chunks and generating flashcards...")
    text = extract_text_from_pdf(pdf_path)
    chunks = chunk_text(text)[:max_chunks]
    raw_flashcards = generate_flashcards_with_llm(chunks)
    text_flashcards = []
    for raw_output in raw_flashcards:
        text_flashcards.extend(parse_llm_output(raw_output))

    print("Extracting figures and captions...")
    figure_flashcards = extract_figures_with_captions(pdf_path)

    combined_flashcards = text_flashcards + figure_flashcards
    save_flashcards_to_tsv(combined_flashcards)
    print(f"Combined flashcards saved to {ANKI_OUTPUT}")

def get_anki_media_folder():
    """Determine the path to Anki's media folder based on the OS."""
    user_folder = "User 1"  # Replace with your Anki profile name if it's not "User 1"
    if platform.system() == "Darwin":  # macOS
        return os.path.expanduser(f"~/Library/Application Support/Anki2/{user_folder}/collection.media")
    elif platform.system() == "Windows":  # Windows
        return os.path.expandvars(f"%APPDATA%\\Anki2\\{user_folder}\\collection.media")
    elif platform.system() == "Linux":  # Linux
        return os.path.expanduser(f"~/.local/share/Anki2/{user_folder}/collection.media")
    else:
        raise Exception("Unsupported operating system.")

def move_images_to_anki(source_folder):
    """Move PNG images from the source folder to Anki's media folder."""
    anki_media_folder = get_anki_media_folder()
    if not os.path.exists(anki_media_folder):
        raise FileNotFoundError(f"Anki media folder not found at {anki_media_folder}")

    # Ensure the source folder exists
    if not os.path.exists(source_folder):
        raise FileNotFoundError(f"Source folder not found at {source_folder}")

    # Move PNG files to Anki's media folder
    for filename in os.listdir(source_folder):
        if filename.endswith(".png"):
            source_path = os.path.join(source_folder, filename)
            destination_path = os.path.join(anki_media_folder, filename)
            shutil.move(source_path, destination_path)
            print(f"Moved: {filename} to {anki_media_folder}")

# Main Execution
pdf_file = input("Enter the path to the PDF file: ")
create_combined_flashcards(pdf_file, max_chunks=3)

'''
# Move images to Anki media folder
try:
    move_images_to_anki(MEDIA_FOLDER)
    print("All images have been successfully moved to Anki's media folder.")
except Exception as e:
    print(f"Error: {e}")
'''
