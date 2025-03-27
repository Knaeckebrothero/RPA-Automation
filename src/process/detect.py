"""
This module contains functions for detecting certain objects in images or strings.
"""
import re
import cv2
import numpy as np
from difflib import SequenceMatcher
from typing import List, Tuple
import logging as log


# Set up logging
log = log.getLogger(__name__)

def tables(bgr_image_array: np.array) -> List[np.array]:
    """
    This function detects the contours of tables in an image.

    It does so by detecting horizontal and vertical lines in the image and combining them to form a mask.
    The contours of the mask are then extracted and filtered based on area to identify the tables.

    :param bgr_image_array: A NumPy array representing the input image in BGR format.
    :return: A list of points representing the contours of the detected tables.
    """
    if len(bgr_image_array.shape) == 3:  # Check if the image is in color
        # Convert to grayscale for structural analysis
        grey_bgr_image_array = cv2.cvtColor(bgr_image_array, cv2.COLOR_BGR2GRAY)
    else:
        # Already grayscale
        grey_bgr_image_array = bgr_image_array

    log.debug(f"Grey image shape: {grey_bgr_image_array.shape}")

    # Create a binary threshold (basically splitting the image into two colors of maximum intensity)
    thresh = cv2.adaptiveThreshold(
        grey_bgr_image_array,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        15,  # Size of the neighborhood considered for thresholding (should be an odd number)
        10   # A constant subtracted from the mean (adjusts sensitivity)
    )
    log.debug(f"Threshold image shape: {thresh.shape}" )

    # Detect horizontal lines
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
    detect_horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
    log.debug(f"Horizontal lines shape: {detect_horizontal.shape}")

    # Detect vertical lines
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    detect_vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
    log.debug(f"Vertical lines shape: {detect_vertical.shape}" )

    # Combine horizontal and vertical lines to form a mask
    table_mask = cv2.addWeighted(detect_horizontal, 0.5, detect_vertical, 0.5, 0.0)
    log.debug(f"Table mask shape: {table_mask.shape}")

    # Find the contours of the mask and filter based on area size
    contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # Filter based on area size (10,000 pixels seems like a reasonable threshold for a table)
    table_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > 10000]

    # Log the contours if log level is set to debug
    if log.getEffectiveLevel() < 20:
        for cnt in table_contours:
            log.debug(f"Table contour area: {cv2.contourArea(cnt)}")

    return table_contours


def rows(table_image: np.array) -> List[Tuple[int, int]]:
    """
    Detect rows in a table by finding horizontal separator lines,
    filtering out small gaps and borders.

    :param table_image: A NumPy array representing the table image
    :return: A list of tuples representing the y-coordinates of rows
    """
    # Convert to grayscale if needed
    if len(table_image.shape) == 3:
        gray = cv2.cvtColor(table_image, cv2.COLOR_BGR2GRAY)
    else:
        gray = table_image

    # Create a binary image focusing on dark lines
    _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)

    # Detect horizontal lines
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)

    # Find contours of the horizontal lines
    contours, _ = cv2.findContours(horizontal_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter for significant horizontal lines (to remove noise)
    min_width = binary.shape[1] * 0.3  # Line should be at least 30% of table width
    line_positions = []

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w > min_width and h < 10:  # Ensure it's wide but not too tall
            line_positions.append(y)

    # Sort line positions
    line_positions.sort()

    # Add table boundaries if needed
    if len(line_positions) == 0:
        # No lines detected, treat the whole table as one row
        return [(0, gray.shape[0])]

    # Create rows between lines
    potential_rows = []

    # Add top of table to first line if needed
    if line_positions[0] > 10:  # Only if there's significant space
        potential_rows.append((0, line_positions[0]))

    # Add rows between lines
    for i in range(len(line_positions) - 1):
        potential_rows.append((line_positions[i], line_positions[i + 1]))

    # Add last line to bottom of table if needed
    if gray.shape[0] - line_positions[-1] > 10:  # Only if there's significant space
        potential_rows.append((line_positions[-1], gray.shape[0]))

    # Filter rows by minimum height (to remove small gaps/borders)
    min_row_height = max(10, gray.shape[0] * 0.03)  # At least 5% of table height or 20px

    filtered_rows = []
    for row_start, row_end in potential_rows:
        row_height = row_end - row_start
        if row_height >= min_row_height:
            filtered_rows.append((row_start, row_end))

    # If all rows were filtered out (unlikely), return the whole table
    if not filtered_rows:
        return [(0, gray.shape[0])]

    return filtered_rows


def cells(row_image: np.array) -> List[Tuple[int, int]]:
    """
    Detect cells in a row by finding significant vertical separator lines.

    :param row_image: A NumPy array representing the row image
    :return: A list of tuples representing the x-coordinates of detected cells
    """
    # Input validation
    if row_image is None or row_image.size == 0:
        return []

    # Convert to grayscale if needed
    if len(row_image.shape) == 3:
        gray = cv2.cvtColor(row_image, cv2.COLOR_BGR2GRAY)
    else:
        gray = row_image

    # Create a binary image - using a lower threshold (180 instead of 240)
    # to focus on actual lines rather than text or noise
    _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)

    # Detect vertical lines - kernel height based on row height
    # This makes the detection more robust for different sized rows
    min_line_height = max(20, int(row_image.shape[0] * 0.5))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, min_line_height))
    vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel, iterations=2)

    # Find contours of vertical lines
    contours, _ = cv2.findContours(vertical_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter for significant vertical lines - must be at least 50% of row height
    significant_lines = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if h > row_image.shape[0] * 0.5:  # Line must be tall enough
            significant_lines.append(x)  # Store x-position of the line

    # Sort lines by x-position
    significant_lines.sort()

    # If no significant vertical lines detected, return the whole row as one cell
    if not significant_lines:
        # Add small margins to avoid border
        margin = 5
        return [(margin, row_image.shape[1] - margin)]

    # Create cells between the detected lines
    cells = []

    # First cell: from left edge to first line
    if significant_lines[0] > 20:  # Only if there's meaningful space
        cells.append((5, significant_lines[0] - 5))

    # Middle cells: between consecutive lines
    for i in range(len(significant_lines) - 1):
        # Only create a cell if there's enough space between lines
        if significant_lines[i+1] - significant_lines[i] > 20:
            cells.append((significant_lines[i] + 5, significant_lines[i+1] - 5))

    # Last cell: from last line to right edge
    if row_image.shape[1] - significant_lines[-1] > 20:
        cells.append((significant_lines[-1] + 5, row_image.shape[1] - 5))

    # If somehow we filtered out all cells, return the whole row
    if not cells:
        return [(5, row_image.shape[1] - 5)]

    return cells


def bafin_id(text: str) -> int | None:
    """
    Extract the BaFin ID from a text string.
    The function looks for patterns like "BaFin-ID 12345678" or "BaFin-ID (wenn bekannt) 12345678"
    and handles potential OCR errors in the surrounding text.

    :param text: The text to search for a BaFin ID
    :return: The 8-digit BaFin ID if found, or an empty string if no valid BaFin ID is found
    """
    if not text:
        log.warning("Empty text provided to extract_bafin_id")
        return None

    # Clean the text - remove extra spaces
    cleaned_text = ' '.join(text.split())
    log.debug(f"Searching for BaFin ID in: {cleaned_text[:100]}...")

    # List of regex patterns to try
    patterns = [
        # Pattern 1: "BaFin-ID" followed by 8 digits (with flexible spacing and punctuation)
        r'[Bb]a[Ff]in[\s\-\.,]*[Ii][Dd][\s\-\.,]*(\d{8})',

        # Pattern 2: 8 digits near "BaFin"
        r'[Bb]a[Ff]in[\s\-\.,]*(\d{8})',

        # Pattern 3: "ID" or "Nr" followed by 8 digits
        r'(?:[Ii][Dd]|[Nn][Rr])[\s\-\.,]*(\d{8})',

        # Pattern 4: 8 digits followed by "wenn bekannt"
        r'(\d{8})[\s\-\.,]*[Ww]enn[\s\-\.,]+[Bb]ekannt',

        # Pattern 5: "wenn bekannt" followed by 8 digits
        r'[Ww]enn[\s\-\.,]+[Bb]ekannt[\s\-\.,]*(\d{8})'
    ]

    # Try each pattern in order
    for i, pattern in enumerate(patterns):
        matches = re.search(pattern, cleaned_text)
        if matches:
            bafin_id = matches.group(1)
            log.info(f"Found BaFin ID {bafin_id} using pattern {i+1}")
            return int(bafin_id)

    # Fallback: Search for isolated 8-digit numbers and evaluate their context
    log.debug("No BaFin ID found with primary patterns, trying fallback approach")
    isolated_numbers = list(re.finditer(r'\b(\d{8})\b', cleaned_text))
    log.debug(f"Found {len(isolated_numbers)} isolated 8-digit numbers")

    for match in isolated_numbers:
        # Get some context around the match
        start = max(0, match.start() - 50)
        end = min(len(cleaned_text), match.end() + 50)
        context = cleaned_text[start:end].lower()

        # Keywords that suggest this might be a BaFin ID
        keywords = ['bafin', 'id', 'nummer', 'kennung', 'bekannt', 'identifikation']

        # Check for similar words in case of OCR errors
        for word in context.split():
            for keyword in keywords:
                similarity = _similar(word, keyword)
                if similarity > 0.7:
                    bafin_id = match.group(1)
                    log.info(f"Found BaFin ID {bafin_id} using context similarity "
                             f" (word: {word}, keyword: {keyword}, similarity: {similarity:.2f})")
                    return int(bafin_id)

    log.warning("No BaFin ID found in the text")
    return None


def _similar(a, b):
    """
    Calculate similarity ratio between two strings
    """
    return SequenceMatcher(None, a, b).ratio()
