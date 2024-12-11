from PIL import Image
import numpy as np
import fitz  # PyMuPDF
import os

def detect_white_margin(image_path, tolerance=250, min_consecutive_white=15):
    # Open the image and convert to a numpy array
    image = Image.open(image_path)
    image_array = np.array(image)

    # Iterate over rows (y-axis)
    height, width, _ = image_array.shape
    consecutive_white_rows = 0

    for y in range(height):
        row = image_array[y, :, :]  # Get the row (all columns for this y)
        if np.all(row >= tolerance):  # Check if all pixels are "white enough"
            consecutive_white_rows += 1
            if consecutive_white_rows >= min_consecutive_white:
                return y  # Return the y-coordinate of the first white row
        else:
            consecutive_white_rows = 0  # Reset if a non-white row is found

    return height  # If no margin is found, return the full height


def extract_figures_with_dynamic_bounds(pdf_path, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    pdf_document = fitz.open(pdf_path)

    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        print(f"Processing Page {page_num + 1}...")

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
                            temp_image_path = os.path.join(output_folder, "temp_image.png")
                            pix.save(temp_image_path)

                            # Detect white margin
                            new_bottom = detect_white_margin(temp_image_path)
                            final_cropped_area = fitz.Rect(x0 - 25, y0 - 10, x1 + 350, y0 + new_bottom)

                            # Render the final cropped area
                            final_pix = page.get_pixmap(clip=final_cropped_area)
                            output_path = os.path.join(output_folder, f"page_{page_num + 1}_figure_margin.png")
                            final_pix.save(output_path)
                            print(f"Extracted figure to {output_path}")

    pdf_document.close()

# Paths
pdf_file = "text1.pdf"
output_dir = "dynamic_margin_figures"

# Run the function
extract_figures_with_dynamic_bounds(pdf_file, output_dir)

