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
CHUNK_SIZE = 3000
KEYWORD_PROMPT = "Extract key words and concepts from the text along with their corresponding definitions, Store this ininformation in a dictionary."

# Function to chunk text into smaller parts
def chunk_text(text, chunk_size):
    words = text.split()
    for i in range(0, len(words), chunk_size):
        yield " ".join(words[i:i + chunk_size])

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
all_keywords = []
for chunk in chunk_text(text, CHUNK_SIZE):
    keywords = extract_keywords(chunk)
    all_keywords.append(keywords)
    
    # Introduce a delay between requests to avoid rate limits
    time.sleep(15)

# Combine all the extracted keywords and definitions
final_keywords = "\n\n".join(all_keywords)

# Print the final structured output
print("\nCollected Keywords and Definitions:")
print(final_keywords.strip())

