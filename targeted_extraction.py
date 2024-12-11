import fitz  # PyMuPDF
import os

def extract_figures_near_labels(pdf_path, output_folder):
    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # Open the PDF
    pdf_document = fitz.open(pdf_path)

    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        print(f"Processing Page {page_num + 1}...")

        # Search for the word "Figure" on the page
        search_results = page.search_for("Figure")
        if not search_results:
            print(f"No 'Figure' label found on page {page_num + 1}.")
            continue

        # Loop through all matches of the word "Figure"
        for i, bbox in enumerate(search_results, start=1):
            # Define the cropping area: adjust the region to the right of "Figure"
            x0, y0, x1, y1 = bbox
            cropped_area = fitz.Rect(x0 - 25, y0 - 10, x1 + 350, y1 + 100)

            # Render the cropped area as an image
            pix = page.get_pixmap(clip=cropped_area)
            output_path = os.path.join(output_folder, f"page_{page_num + 1}_figure_{i}.png")
            pix.save(output_path)

            print(f"Extracted figure {i} on page {page_num + 1} to {output_path}")

    pdf_document.close()

# Paths
pdf_file = "practice_extraction_text1.pdf"
output_dir = "extracted_figures_by_labels"

# Run the function
extract_figures_near_labels(pdf_file, output_dir)

