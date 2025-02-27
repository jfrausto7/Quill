import numpy as np
import pytesseract

def find_label_coords(image_path, phrases):
    """
    find_label_coordinates uses Google's Tesseract OCR to find the x, y pixel coordinates of the 
    labels on a form image. The function takes in an image and a list of phrases to search for in 
    the image. It returns a list of tuples, where each tuple contains the x, y pixel coordinates of 
    the top-left corner of a label.
    """
    data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
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

def main():
    image_path = "W-2.png"
    phrases = ["Employee's social security number", "Employer identification number", 
               "Wages, tips, other compensation"]
    coords = find_label_coords(image_path, phrases)

if __name__ == "__main__":
    main()
