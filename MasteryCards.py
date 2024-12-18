import os
import re
import time
import PyPDF2
from groq import Groq
import fitz  #for PDF handling
from PIL import Image
import numpy as np
import random

# constant variables
CHUNK_SIZE = 2700  # What I have found to work with GROQ
LLM_MODEL = "llama3-8b-8192"  # Model used
MEDIA_FOLDER = "anki_media"  # file for the pngs of the figures
TSV_FILE = "flashcards.tsv"  # Flashcards TSV file name

# Initialize
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Prompt to create standard text content flashcards
KEYWORD_PROMPT = """
You are tasked with extracting structured information from the provided text. For each keyword or concept, provide the following in a consistent format:

1. **Term**: The key term or concept.
2. **Definition**: A concise and clear definition of the term or concept. Include relevant details or examples only if they are general and can stand on their own.

Format the output exactly like this (including all symbols and delimiters):

### BEGIN ENTRY ###
Term: [Term]
Definition: [Definition]
### END ENTRY ###

Ensure the following:
- Only create flashcards for general concepts or topics that make sense independently, outside of the current text. Avoid highly specific examples, scenarios, or terms that require additional context to be understood.
- Ensure the front and back of the flashcard are meaningful and complete on their own.
- If a definition cannot be generated for a term, do not create a flashcard for it. Skip such terms entirely.
- Use precise, concise language.
- Exclude unrelated or random words, redundant terms, or repeated examples.
- Ensure the output is ready to be concatenated with outputs from other chunks without ambiguity.

Do not include placeholder phrases like "Not provided in the text" or "No definition found." If a good definition cannot be generated, simply skip that term.
"""

# this function extracts text from a pdf file using PyPDF2's PdfReader function
def extract_text_from_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text

# this function splits chunks using the token size limits set earlier
def chunk_text(text, chunk_size=CHUNK_SIZE):
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

# this function generates flashcards for the text chunks using a call to the LLM
# with the keyword prompt we set earlier
def generate_flashcards_with_llm(chunks):
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

        time.sleep(10)

    return flashcards

# format the LLM output into front and back of flashcards using the ### BEGIN ENTRY ### and ### END ENTRY ### that was insisted on
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

# this function runs the code on the first number chunks of the pdf (used for testing) but also generally shows the pipeline
def create_content_flashcards(pdf_path, max_chunks=None):
    text = extract_text_from_pdf(pdf_path)

    # Chunk the text, limits it to the first `max_chunks` set in def line
    chunks = chunk_text(text)[:max_chunks]

    # Generate flashcards for limited chunks using LLM
    raw_flashcards = generate_flashcards_with_llm(chunks)

    # Parse and format flashcards
    parsed_flashcards = []
    for raw_output in raw_flashcards:
        parsed_flashcards.extend(parse_llm_output(raw_output))

    return parsed_flashcards

def remove_duplicates(flashcards):
    seen = set()  # track unique fronts
    unique_flashcards = []

    for front, back in flashcards:
        if front not in seen: 
            unique_flashcards.append((front, back))
            seen.add(front)

    return unique_flashcards


# Prompt for refining captions of prompts into a front of a flashcard
CAPTION_PROMPT = """
You are tasked with analyzing a provided caption for a figure and creating the front of a flashcard. Your goal is to interpret what the figure generally represents based on the caption, focusing on the sentence immediately following "Figure X.X" (or similar). From this, generate a meaningful, concise question or description for the front of the flashcard.

The question or description should focus **only on the topic or concept** represented by the figure, without directly referring to "the figure," "the graph," "Figure X.X," or any visual elements that are not visible to the learner. The front of the flashcard should be guessable and make sense **on its own**, even without seeing the figure.

Use the following strict format and instructions:

### BEGIN FLASHCARD ###
Prompt: [Write a clear and concise question or description for the front of a flashcard. Focus on the general topic, key concept, or relationship illustrated by the figure. Avoid referring to the figure, graph, or any visual elements directly.]
### END FLASHCARD ###

Guidelines:
- Pay close attention to the sentence following "Figure X.X" as it explains the concept or topic being shown.
- Write a question or description about the broader **topic, key relationship, or principle** the figure represents.
- Do not mention or reference the figure, graph, or visual elements directly (e.g., avoid phrases like “the figure shows” or “the graph represents”).
- Ensure clarity and conciseness so the learner can understand and guess the back effectively without needing to see the figure.
- Avoid vague phrasing or overly contextual details that don’t contribute to understanding.

Provide the refined flashcard prompt in the exact format described above. Do not include explanations, footnotes, or justifications outside the specified format.
"""

#check directory exists
def ensure_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)

# extracting captions and surrounding text of a labeled figure
def extract_captions_from_text(page_text, max_words=100):
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

# this functin detects a large white margin around a figure so it can crop
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

# Caption refine using prompt from above
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

# function to extract figures and captions from the pdf 
def extract_figures_with_captions(pdf_path):
    pdf_document = fitz.open(pdf_path)
    ensure_directory(MEDIA_FOLDER) # checks the folder for saving the pngs exists
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

# just saving the flashcards to a TSV file
def save_flashcards_to_tsv(flashcards, filename="flashcards.tsv"):
    file_path = os.path.join(os.getcwd(), filename)
    
    with open(file_path, "w") as tsv_file:
        for front, back in flashcards:
            tsv_file.write(f"{front}\t{back}\n")

# function to now ask for pdf instead of have set in this python file
def ask_for_pdf_file():
    while True:
        pdf_file = input(
            "Enter the PDF file name you want to analyze (ex: my_probability_textbook.pdf): "
        ).strip()
        
        if not os.path.isfile(pdf_file):  # Check if file exists
            print(f"File '{pdf_file}' not found. Please try again. Make sure in your finder it is in the same working directory as this python file")
            continue
        
        return pdf_file

# shuffles the flashcards
def jumble_flashcards(flashcards):
    shuffled_flashcards = flashcards[:]
    random.shuffle(shuffled_flashcards)
    return shuffled_flashcards

def execution():
    # ask for pdf file path to work on
    pdf_file = ask_for_pdf_file()

    # content flashcards
    print("Extracting pdf content...")
    raw_content_flashcards = create_content_flashcards(pdf_file)
    content_flashcards = remove_duplicates(raw_content_flashcards)

    # figures flashcards
    print("Extracting figures and captions...")
    figures_flashcards = extract_figures_with_captions(pdf_file)

    # save both sets of flashcards in a TSV format for Anki
    all_flashcards = content_flashcards + figures_flashcards
    flashcards = jumble_flashcards(all_flashcards)
    print(f"Saving flashcards to {TSV_FILE}...")
    save_flashcards_to_tsv(flashcards)

    print("Flashcards created successfully! Make sure to follow the instruction of how to move the images to Anki's media folder.")

# executions!
execution()