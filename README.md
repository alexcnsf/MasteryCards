# MasteryCards

## Overview
MasteryCards is my final project for CS 181: Special Topics for CS. I am a huge user of flashcards to study for all of my college courses as I personally find it much more effective for memorization compared to readings textbooks or watching lectures. Because of this I create hundreds of flashcards each semester and the stack of them on my desk, overflowing from my limited number of flashcard cases, was my inspiration for this final project. In this project I aim to create a system that can take a pdf textbook, specifically my probability textbook, *Probability and Statistics Fourth Edition* by DeGroot and Schervish, and construct all the flashcards I would need for the topics I am covering.

## Features

These are the features it includes:
- Take the input of a pdf textbook and chunk it by Chapter, Subsections, and then Theroem and Defintions until it is below the token limit.
- It accurately identifies the location of and takes snapshots of figures in this textbook without cutting the figure itself off or including other text around the figures.
- It uses the chunked text to create the flashcards of important topics and keywords (front) and explanations and examples (back) in a tab-seperated CSV format that is compatable with the flashcard software Anki.
- It also creates flashcards for the figures from the textbook by scraping text around the figure, such as its caption, and prompts the LLM to create an accurate front side for the flashcard with the image on the back visualizing the topic.
- All of these flashcards from the normal chunked text and the figures are compiled and formatted into a tab-seperated values (TSV) format that is compatible with Anki.
- Next it automatically moves the images of the figures to the correct folder inside of the Anki Application in order for them to be shown on your flashcards.
- Next you are able to take the TSV flashcards that have been created and go over to the Anki application and import them as a new deck. From there you can start studying!

## Setup

Go ahead and install the all the requirements need for this project using:
```
pip install -r requirements.txt
```

Next go to [Groq](https://console.groq.com/keys) and generate an API key. 

Set the key in your terminal enviroment using:
```
export GROQ_API_KEY="your_api_key_here"
```

You can check this is done correctly by running:
```
echo $GROQ_API_KEY
```

Upload the pdf you want to work with to your directory so it can be accessed in future steps.

## Running it

To start the program use the command 
```
$ python3 MasterCards.py
```

You will be prompted with:
```
Enter the path to the PDF file:
```

For which you can type in the name or path to the file in your directory.

This will then look something like this:
```
Enter the PDF file name (with extension): text1.pdf
Processing chunk 1 of 220...
Processing chunk 2 of 220...
Processing chunk 3 of 220...
```


Expecting this to take a few minutes but after this is complete and you have to copy the contents of the created folder **anki_media** and paste it into the folder located at:
On Windows:\Users\<YourUsername>\AppData\Roaming\Anki2\<YourProfileName>\collection.media
On MacOs: ~/Library/Application Support/Anki2/<YourProfileName>/collection.media
On Linux: ~/.local/share/Anki2/<YourProfileName>/collection.media


This is to move the png files you have collected from your pdf onto Anki so they can be displayed on your flashcards. Unfortunately this has to be done manually as my attempt to automize it have all failed.


Next you open the Anki2 application and press **Import Files**, then navigate to and select the **flashcards.tsv** file in your finder.

Import this and you are ready starting studying!


## Features In-depth


Figure Deteching:

I detected figures by creating an array of the pixels around matches to Bolded words 'figure' and tracked till I found large enough marings which would match the end of a figures.

```
image = Image.open(image_path)
image_array = np.array(image)
height, width, _ = image_array.shape
```

I used a width of 15 white pixels to signal a margin break after some roudns of trial and error.

Prompts for constructed output:

I used examples and symbols in order to seperate results that I could programmatically format afterwards.

```
CAPTION_PROMPT = """
You are tasked with analyzing a provided caption for a figure and creating the front of a flashcard. Your goal is to interpret what the figure generally represents based on the caption and generate a meaningful, concise question or description for the front of the flashcard. Use the following strict format and instructions:

### BEGIN FLASHCARD ###
Prompt: [Write a general question or description suitable for the front of a flashcard. The prompt should focus on the broader concept or idea represented by the figure, rather than overly specific details. Ensure the prompt provides enough context for a learner to understand the figure's purpose.]
### END FLASHCARD ###
"""

KEYWORD_PROMPT = """
You are tasked with extracting structured information from the provided text. For each keyword or concept, provide the following in a consistent format:

1. **Term**: The key term or concept.
2. **Definition**: A concise and clear definition of the term or concept. Include relevant details or examples if explicitly available in the text.

### BEGIN ENTRY ###
Term: [Term]
Definition: [Definition]
### END ENTRY ###
"""
```



Results:

1. **Breadth** Of the 20 predecided topics to judge the breadth of the flashcards for the three chapters I selected these 16 were included in some terminology:

Conditional Probability, Bayes’ Theorem, Law of Total Probability, Independent Events, Multiplication Rule for Probabilities, Conditional Independence, Partitions of a Sample Space, Sample Spaces, Events and Outcomes, Disjoint Events, Uniform Probability Distribution, Random Variables, Expected Value, Joint Probability, Marginal Probability, and Law of Large Numbers

While these four where not: Mutual Independence, Mutually Exclusive Events, Augmented Experiment, and Probability Trees

2. **Quality**



3. **Figure Accuracy**


