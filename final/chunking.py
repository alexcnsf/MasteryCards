import re
import PyPDF2
import fitz  # PyMuPDF for font analysis

CHUNK_SIZE = 2700  # Approximate token limit


def extract_text_from_pdf(pdf_path):
    """Extracts text from a given PDF file."""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text


def find_theorem_or_definition_starts(text):
    """Identifies section starts based on 'Theorem' or 'Definition' followed by a number."""
    pattern = r"\b(Theorem|Definition)\s\d+\.\d+(\.\d+)?\b"
    matches = [(m.start(), m.group()) for m in re.finditer(pattern, text)]
    return matches


def split_large_section(section, chunk_size):
    """Splits a large section into smaller chunks respecting paragraph breaks."""
    chunks = []
    while len(section) > chunk_size:
        split_point = section[:chunk_size].rfind("\n\n")  # Split at the last paragraph break
        if split_point == -1:
            split_point = chunk_size  # If no paragraph break, split arbitrarily
        chunks.append(section[:split_point].strip())
        section = section[split_point:].strip()
    if section:
        chunks.append(section)
    return chunks


def chunk_text_by_theorem_definition(text, section_starts, chunk_size=CHUNK_SIZE):
    """Splits the text into chunks based on 'Theorem' or 'Definition' followed by a number."""
    chunks = []

    for i, (start, marker) in enumerate(section_starts):
        end = section_starts[i + 1][0] if i + 1 < len(section_starts) else len(text)
        section = text[start:end].strip()

        # Check if the section needs further splitting
        if len(section) > chunk_size:
            chunks.extend(split_large_section(section, chunk_size))
        else:
            chunks.append(section)

    return chunks


def main():
    pdf_path = input("Enter the path to the PDF file: ")
    try:
        # Extract text from the PDF
        pdf_text = extract_text_from_pdf(pdf_path)

        # Identify section starts based on 'Theorem' or 'Definition'
        section_starts = find_theorem_or_definition_starts(pdf_text)
        print(f"Section starts detected: {section_starts}")

        # Chunk the text
        chunks = chunk_text_by_theorem_definition(pdf_text, section_starts, chunk_size=CHUNK_SIZE)
        print(f"Number of chunks created: {len(chunks)}")

        # Output results
        for i, chunk in enumerate(chunks):
            print(f"Chunk {i + 1} (Length: {len(chunk)}):\n{chunk}\n{'-' * 50}")

        # Save chunks to a file
        output_path = input("Enter the output filename (e.g., chunks.txt): ")
        with open(output_path, 'w') as output_file:
            for i, chunk in enumerate(chunks):
                output_file.write(f"Chunk {i + 1} (Length: {len(chunk)}):\n{chunk}\n{'-' * 50}\n")

        print(f"Chunks saved to {output_path}")

    except FileNotFoundError:
        print(f"File not found: {pdf_path}")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
