import os
import re
import time
import PyPDF2  # For PDF text extraction
from groq import Groq  # Assuming you have a Groq client library

# Constants
CHUNK_SIZE = 2700  # Approximate token limit for text chunks
ANKI_OUTPUT = "flashcards.tsv"

# Initialize Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# LLM Prompt
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


# --- Helper Functions ---
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
            model="llama3-8b-8192",
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

def create_flashcards(pdf_path, max_chunks=2):
    """Generate flashcards from the first few chunks of a PDF."""
    text = extract_text_from_pdf(pdf_path)

    # Chunk the text and limit to the first `max_chunks`
    chunks = chunk_text(text)[:max_chunks]

    # Generate flashcards for limited chunks using LLM
    raw_flashcards = generate_flashcards_with_llm(chunks)

    # Parse and format flashcards
    parsed_flashcards = []
    for raw_output in raw_flashcards:
        parsed_flashcards.extend(parse_llm_output(raw_output))

    # Save flashcards to a TSV file for Anki
    with open(ANKI_OUTPUT, "w") as f:
        for front, back in parsed_flashcards:
            f.write(f"{front}\t{back}\n")

    print(f"Flashcards saved to {ANKI_OUTPUT}")


# --- Main Execution ---
pdf_file = "practice_text.pdf"
create_flashcards(pdf_file, max_chunks=2)

