import argparse
import chardet
import os
import fulltext
import time
from groq import Groq  # Assuming you have a Groq client library
import PyPDF2  # For PDF extraction

# Function to detect encoding using chardet
def detect_encoding(file_path):
    with open(file_path, 'rb') as f:
        raw_data = f.read()
        result = chardet.detect(raw_data)
        return result['encoding']

# Function to read the file with detected encoding
def read_file_with_encoding(file_path):
    encoding = detect_encoding(file_path)
    if encoding is None:
        raise ValueError("Could not detect file encoding.")
    with open(file_path, 'r', encoding=encoding) as f:
        return f.read()

# Function to extract text from PDF using PyPDF2
def extract_text_from_pdf(file_path):
    try:
        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            return text.strip() if text else None
    except Exception as e:
        print(f"PyPDF2 failed to extract text from PDF: {e}")
        return None

# Function to extract text from the file using fulltext and fallback to PyPDF2 and chardet
def extract_text(file_path):
    try:
        return fulltext.get(file_path)
    except Exception as e:
        print(f"fulltext failed: {e}")
    
    if file_path.endswith('.pdf'):
        print("Attempting to extract text using PyPDF2...")
        pdf_text = extract_text_from_pdf(file_path)
        if pdf_text:
            return pdf_text

    print("Attempting to detect encoding with chardet...")
    try:
        return read_file_with_encoding(file_path)
    except Exception as e:
        print(f"Failed to read the file even after detecting encoding: {e}")
        exit(1)

# Argument parser
parser = argparse.ArgumentParser()
parser.add_argument('filename')
args = parser.parse_args()

# Read the document text
text = extract_text(args.filename)

if not text:
    print("No text could be extracted from the document.")
    exit(1)

# Initialize the Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Define chunk size and prompt for keyword extraction
CHUNK_SIZE = 2700
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


#Function to chunk text into smaller parts
def chunk_text(text, chunk_size):
    words = text.split()
    return [ " ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size) ]

# Extract keywords and definitions from each chunk
def extract_keywords(chunk):
    response = client.chat.completions.create(
        messages=[
            {'role': 'system', 'content': KEYWORD_PROMPT},
            {'role': 'user', 'content': chunk}
        ],
        model="llama3-8b-8192",
    )
    return response.choices[0].message.content

# Process each chunk and collect keywords/definitions
chunks = chunk_text(text, CHUNK_SIZE)
total_chunks = len(chunks)
all_keywords = []

print(f"Total chunks to process: {total_chunks}")

for i, chunk in enumerate(chunks, start=1):
    print(f"Processing chunk {i}/{total_chunks}...")
    keywords = extract_keywords(chunk)
    all_keywords.append(keywords)

    # Print the output of the current chunk
    print(f"Output for chunk {i}/{total_chunks}:")
    print(keywords)  
 
    # Introduce a delay between requests to avoid rate limits
    time.sleep(15)

    # Progress update
    print(f"Chunk {i}/{total_chunks} completed.")

# Combine all the extracted keywords and definitions
final_keywords = "\n\n".join(all_keywords)

# Print the final structured output
print("\nCollected Keywords and Definitions:")
print(final_keywords.strip())

