import numpy as np
import pytesseract
import logging

def find_label_coords(img_path, phrases):
    """
    find_label_coordinates uses Google's Tesseract OCR to find the x, y pixel coordinates of the 
    labels on a form image. The function takes in an image and a list of phrases to search for in 
    the image. It returns a list of tuples, where each tuple contains the x, y pixel coordinates of 
    the top-left corner of a label.
    """
    data = pytesseract.image_to_data(img_path, output_type=pytesseract.Output.DICT)
    words = data["text"]
    coords = {}
    lost_keys = []

    num_found = 0 
    for raw_phrase in phrases:  
        found = False
        phrase = raw_phrase.replace("'", "’") # sometimes apostrophes trip up the OCR
        phrase_words = phrase.split()
        phrase_length = len(phrase_words)
        for i in range(len(words) - phrase_length + 1):
            # Check if the consecutive words match the phrase
            if words[i:i + phrase_length] == phrase_words:
                x, y = data["left"][i], data["top"][i] + data["height"][i]
                logging.info(f"Found '{phrase}' at: x1={x}, y1={y}")
                coords[phrase] = (x, y)
                num_found += 1
                found = True
        if not found:
            logging.info(f"Unable to find '{phrase}'")
            lost_keys.append(raw_phrase)
    print(f"Found {num_found} out of {len(phrases)} fields")

    return lost_keys, coords

def main():
    image_path = "W-2.png"
    phrases = ["Employee's social security number", "Employer identification number", 
               "Wages, tips, other compensation"]
    coords = find_label_coords(image_path, phrases)

if __name__ == "__main__":
    main()
