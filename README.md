# MasteryCards

## Overview
MasteryCards is my final project for CS 181: Special Topics for CS. I am a huge user of flashcards to study for all of my college courses as I personally find it much more effective for memorization compared to readings textbooks or watching lectures. Because of this I create hundreds of flashcards each semester and the stack of them on my desk, overflowing my limited number of flashcard holders, was my inspiration for this final project. In this project I aim to create a system that can take a pdf textbook, specifically my probability textbook, *Probability and Statistics Fourth Edition* by DeGroot and Schervish, and create all the flashcards I would need for the topics I was covering.

## Features

These are the features it includes:
- Take the input of a pdf textbook and chunk it by Chapter, Subsections, and then Theroem and Defintions until it is below the token limit.
- It accurately identifies the location of and takes snapshots of figures in this textbook without cutting the figure itself off or including other text around the figures.
- It uses the chunked text to create the flashcards of important topics and keywords (front) and explanations and examples (back).
- It also creates flashcards for the figures from the textbook by scraping text around the figure, such as its caption, and prompts the LLM to create an accurate front side for the flashcard with the image on the back visualizing the topic.
- 


## Setup

```
pip install -r requirements.txt
```

First go to Groq and generate an API key. Set the key in your enviroment using this command:
```
export GROQ_API_KEY="your_api_key_here"
echo $GROQ_API_KEY
```

## Running it

## Features In-depth
