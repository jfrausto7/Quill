import numpy as np
import cv2
import pytesseract


def find_text_coordinates(image, phrases):
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    words = data["text"]
    coords = []

    for phrase in phrases:    
        phrase_words = phrase.split()
        phrase_length = len(phrase_words)
        for i in range(len(words) - phrase_length + 1):
            # Check if the consecutive words match the phrase
            if words[i:i + phrase_length] == phrase_words:
                x1, y1 = data["left"][i], data["top"][i]
                
                print(f"Found '{phrase}' at: x1={x1}, y1={y1}")
                coords.append((x1, y1))

    return coords


if __name__ == "__main__":
    # Load the form image
    image_path = "W-2.png"
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) # to grayscale

    phrases = ["Employee's social security number", "Employer identification number", "Wages, tips, other compensation"]

    coords = find_text_coordinates(gray, phrases)
    print(coords)