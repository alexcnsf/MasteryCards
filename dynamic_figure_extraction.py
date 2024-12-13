from PIL import Image
import numpy as np
import fitz  # PyMuPDF
import os
import re


def detect_white_margin(image_path, tolerance=250, min_consecutive_white=15):
    """Detect the white margin in an image to crop dynamically."""
    image = Image.open(image_path)
    image_array = np.array(image)

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


def extract_captions_from_text(page_text, max_words=25):
    """Extract captions for labeled figures like 'Figure 2.1'."""
    pattern = r"(Figure\s\d+\.\d+(\.\d+)?)"
    matches = re.finditer(pattern, page_text)

    captions = []

    for match in matches:
        figure_label = match.group(0)  # Capture the figure label (e.g., 'Figure 2.1')
        start_index = match.end()  # Start after the figure label
        remaining_text = page_text[start_index:].strip()

        # Extract up to max_words or until the next period
        words = remaining_text.split()
        caption = " ".join(words[:max_words])
        captions.append((figure_label, caption))

    return captions


def extract_figures_with_captions(pdf_path, output_folder):
    """Extract figures and their captions from a PDF."""
    os.makedirs(output_folder, exist_ok=True)
    pdf_document = fitz.open(pdf_path)

    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        print(f"Processing Page {page_num + 1}...")

        # Extract raw text for captions
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
                            temp_image_path = os.path.join(output_folder, "temp_image.png")
                            pix.save(temp_image_path)

                            # Detect white margin
                            new_bottom = detect_white_margin(temp_image_path)
                            final_cropped_area = fitz.Rect(x0 - 25, y0 - 10, x1 + 350, y0 + new_bottom)

                            # Render the final cropped area
                            final_pix = page.get_pixmap(clip=final_cropped_area)
                            figure_output_path = os.path.join(output_folder, f"page_{page_num + 1}_figure_margin.png")
                            final_pix.save(figure_output_path)
                            print(f"Extracted figure to {figure_output_path}")

                            # Find the corresponding caption
                            caption = next((cap[1] for cap in captions if cap[0] in span["text"]), None)
                            caption_output_path = os.path.join(output_folder, f"page_{page_num + 1}_caption.txt")

                            # Save figure and caption together
                            with open(caption_output_path, "w") as caption_file:
                                caption_file.write(f"Figure: {figure_output_path}\n")
                                caption_file.write(f"Caption: {caption}\n" if caption else "Caption: None\n")
                                print(f"Caption saved to {caption_output_path}")

    pdf_document.close()


# Paths
pdf_file = "text1.pdf"  # Replace with your PDF file name
output_dir = "dynamic_margin_figures_with_captions"  # Output directory

# Run the function
extract_figures_with_captions(pdf_file, output_dir)

