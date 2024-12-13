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

## Running it

## Features In-depth
