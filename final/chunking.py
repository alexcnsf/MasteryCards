import re
import PyPDF2
import fitz  # PyMuPDF for font size analysis

CHUNK_SIZE = 2700  # Approximate token limit


def extract_text_from_pdf(pdf_path):
    """Extracts text from a given PDF file."""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text


def find_section_starts_by_font_size(pdf_path):
    """Identifies section breaks based on large font sizes."""
    doc = fitz.open(pdf_path)
    section_starts = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    if span["size"] > 11:  # Adjust font size threshold as needed
                        text = span["text"].strip()
                        if text:
                            section_starts.append((page_num, text))

    doc.close()
    return section_starts


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


def chunk_text_by_sections(text, section_starts, chunk_size=CHUNK_SIZE):
    """Splits the text into chunks based on logical sections."""
    chunks = []

    for i, (page_num, marker) in enumerate(section_starts):
        start = text.find(marker)
        end = text.find(section_starts[i + 1][1]) if i + 1 < len(section_starts) else len(text)
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

        # Identify section starts by font size
        section_starts = find_section_starts_by_font_size(pdf_path)

        # Chunk the text
        chunks = chunk_text_by_sections(pdf_text, section_starts, chunk_size=CHUNK_SIZE)

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

