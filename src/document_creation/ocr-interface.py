import numpy as np
import cv2
import pytesseract

if __name__ == "__main__":
    # Load the form image
    image_path = "W-2.png"
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) # to grayscale

    # Extract text
    text = pytesseract.image_to_string(gray)

    print("Extracted Text:\n", text)
    # Convert image to binary (thresholding)
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

    # Find contours (detect form field outlines)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Define a blank threshold (area of detected box without text)
    blank_fields = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        roi = gray[y:y+h, x:x+w]
        text_in_box = pytesseract.image_to_string(roi).strip()

        if not text_in_box:  # If no text detected, it's a blank
            blank_fields.append((x, y, w, h))

    print("Blank fields found:", blank_fields)

    # Draw rectangles around detected blank fields
    for (x, y, w, h) in blank_fields:
        cv2.rectangle(image, (x, y), (x + w, y + h), (0, 0, 255), 3)  # Red box

    cv2.imwrite("W-2_blanks.png", image)
    print("Highlighted blanks saved as W-2_blanks.png")