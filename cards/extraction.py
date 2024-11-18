import PyPDF2

def extract_text_from_pdf(pdf_path):
    """Extracts text from a given PDF file."""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text

def main():
    # Prompt the user for the PDF file path
    pdf_path = input("Enter the path to the PDF file: ")

    try:
        # Extract text from the provided PDF
        pdf_text = extract_text_from_pdf(pdf_path)

        # Prompt for the output filename
        output_path = input("Enter the output filename (e.g., output.txt): ")
        with open(output_path, 'w') as output_file:
            output_file.write(pdf_text)
        
        print(f"Text extracted and saved to {output_path}")
    
    except FileNotFoundError:
        print(f"File not found: {pdf_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()

