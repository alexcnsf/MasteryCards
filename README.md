## MasteryCards

# Overview


# Features



# Implementation

First go to Groq and generate an API key. Set the key in your enviroment using this command:
```
export GROQ_API_KEY="your_api_key_here"
echo $GROQ_API_KEY
```

Completed:

1. Collect PDFs to practice with
2. Make python file to scrape most information from the files
3. Create python files to take pdfs, scrape them, and chunk them into input sizes.
4. Create process for prompting the LLM for key words and their defintions for each chunk.

To-Dos:

5. Have the outputs organized into CSVs that appened to each other across chunks.
6. Connect all tasks to work together after input of a document, no matter how slow.

New tasks:

1. Extracting Figures and Their References from the PDF
Extract Figures with OCR or Libraries: Tools like PyMuPDF (fitz), pdfminer, or pdfplumber can extract figures as images. If figures have associated captions (e.g., "Figure 1.1"), OCR libraries like Tesseract can extract these captions and associate them with the figures.
Locate Figure Mentions in Text: Text chunking can identify references to figures (e.g., "see Figure 1.1") in the surrounding text.
2. Chunking Text and Matching with Figures
Chunk the Text: Use your current LLM-driven chunking method to segment the text into meaningful blocks (e.g., sections or paragraphs).
Match Figures to Text: If a figure reference appears in a chunk (e.g., "Figure 2.3"), associate the corresponding figure with that chunk. This can be achieved by parsing the PDF's structure or by checking positional proximity (some libraries like PyMuPDF provide positional data for text and images).
3. Generating Flashcards
LLM for Definitions/Explanations: Feed the chunk (text + associated figure reference) into your LLM prompt to generate a structured flashcard. The prompt might look like:
css
Copy code
Context: {chunk of text}
Figure: {figure description or caption if available}
Task: Generate a flashcard including the figure description.
Include Figure Image: Format the flashcard output in Anki-compatible HTML or Markdown, embedding the figure image (extracted from the PDF).
4. Cropping Figures from the PDF
Use libraries like PyMuPDF or Pillow to extract and crop the figure images from the PDF. Once extracted, save the figure images as files and embed them in the Anki flashcard HTML.
5. Integrating into Anki
Create Anki-compatible cards (e.g., using genanki for Python) with:
The text explanation/definition as the question.
The figure image embedded in the answer.
Challenges and Solutions
PDF Complexity: Some PDFs have figures stored as vector graphics or split across multiple objects. A robust library like PyMuPDF can handle these cases better.

Solution: Test on a few sample pages first and adjust your extraction method.
Matching Figures to Text: Figure references might not be explicit.

Solution: Use position-based heuristics (e.g., find the nearest chunk above or below a figure).
Embedding Images in Anki: Ensure images are saved in a directory and linked properly.

Solution: Use Anki's image embedding format (e.g., <img src="path_to_image.jpg">).
Overall Feasibility
Yes, this is feasible. The workflow involves:

Extracting text, figures, and figure references from the PDF.
Matching figures to their corresponding text chunks.
Feeding this information into your LLM for structured flashcard creation.
Formatting the output in Anki-compatible HTML/Markdown.
Suggested Tools and Libraries
PDF Processing: PyMuPDF, pdfplumber
OCR: Tesseract
Image Processing: Pillow
Flashcard Creation: genanki
LLM Integration: OpenAI API or similar


export GROQ_API_KEY="your_api_key_here"
echo $GROQ_API_KEY

