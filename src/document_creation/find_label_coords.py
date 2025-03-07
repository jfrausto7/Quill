import pytesseract
from PIL import Image
import logging
import unicodedata

def normalize_text(text):
    """
    Normalize text by converting to lowercase, removing extra spaces,
    and normalizing unicode characters
    """
    if not text:
        return ""
    # Convert to lowercase
    text = text.lower()
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    # Remove extra spaces
    text = ' '.join(text.split())
    return text

def find_label_coords(img_path, field_labels):
    """
    Find the coordinates of field labels in an image.
    
    Args:
        img_path: Path to the image file
        field_labels: List of field label strings to search for
    
    Returns:
        Tuple of (lost_keys, label_coords) where:
            lost_keys: List of field labels that couldn't be found
            label_coords: Dictionary mapping found field labels to their coordinates
    """
    try:
        # Extract text and bounding box data from the image
        image = Image.open(img_path)
        ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        
        # Create a normalized version of field labels for case-insensitive matching
        normalized_field_labels = [normalize_text(label) for label in field_labels]
        
        # Build a mapping of original labels to normalized labels
        label_mapping = {normalize_text(label): label for label in field_labels}
        
        # Extract words and their bounding boxes
        words = ocr_data['text']
        word_boxes = []
        for i in range(len(words)):
            if int(ocr_data['conf'][i]) > 60:  # Filter by confidence level
                x, y, w, h = (
                    ocr_data['left'][i],
                    ocr_data['top'][i],
                    ocr_data['width'][i],
                    ocr_data['height'][i]
                )
                word_boxes.append((normalize_text(words[i]), (x, y, w, h)))
        
        # Find matches for each field label
        label_coords = {}
        lost_keys = []
        
        for norm_label in normalized_field_labels:
            original_label = label_mapping[norm_label]
            found = False
            
            # Try to find exact matches
            for word, (x, y, w, h) in word_boxes:
                if norm_label == word:
                    label_coords[original_label] = (x, y)
                    found = True
                    break
            
            # If no exact match, try to find partial matches
            if not found:
                # Split the normalized label into words
                label_words = norm_label.split()
                
                # Try to find sequences of words that match the label
                for i in range(len(word_boxes) - len(label_words) + 1):
                    match = True
                    for j in range(len(label_words)):
                        if label_words[j] != word_boxes[i + j][0]:
                            match = False
                            break
                    
                    if match:
                        # Get coordinates of the first word in the sequence
                        x, y, _, _ = word_boxes[i][1]
                        label_coords[original_label] = (x, y)
                        found = True
                        break
            
            if not found:
                lost_keys.append(original_label)
        
        print(f"Found {len(label_coords)} labels, missing {len(lost_keys)} labels")
        print(f"Found labels: {list(label_coords.keys())}")
        print(f"Missing labels: {lost_keys}")
        
        return lost_keys, label_coords
    
    except Exception as e:
        logging.error(f"Error in find_label_coords: {e}")
        return field_labels, {}  # Return all keys as lost if there's an error

def main():
    image_path = "W-2.png"
    phrases = ["Employee's social security number", "Employer identification number", 
               "Wages, tips, other compensation"]
    coords = find_label_coords(image_path, phrases)

if __name__ == "__main__":
    main()
