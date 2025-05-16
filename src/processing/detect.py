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


def normalize_image_resolution(image, target_dpi=400):
    """
    Normalize image to a standard resolution based on target DPI.

    :param image: Input image (numpy array)
    :param target_dpi: Target DPI to normalize to (default 400)
    :return: Resized image normalized to target DPI
    """
    # Get current image dimensions
    h, w = image.shape[:2]

    # If the image has metadata with actual DPI, use that
    # For this example, we'll estimate based on common document sizes
    # A typical A4 document is 8.27 × 11.69 inches
    # At 600 DPI, that would be approximately 4960 × 7016 pixels

    estimated_dpi = estimate_dpi(h, w)

    # Calculate scaling factor
    scale_factor = target_dpi / estimated_dpi

    # Resize the image
    if scale_factor != 1.0:
        new_w = int(w * scale_factor)
        new_h = int(h * scale_factor)
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return resized

    return image


def estimate_dpi(height, width):
    """
    Estimate the DPI of an image based on its dimensions.
    This is a rough estimation assuming standard document sizes.

    :param height: Image height in pixels
    :param width: Image width in pixels
    :return: Estimated DPI
    """
    # Assuming the document is A4 (8.27 × 11.69 inches)
    # Longest dimension is usually height for portrait orientation
    longest_dimension = max(height, width)
    longest_inch = 11.69  # inches

    estimated_dpi = longest_dimension / longest_inch

    # Set reasonable bounds
    if estimated_dpi <= 75:
        return 75
    elif estimated_dpi >= 1200:
        return 1200

    return estimated_dpi


def tables(bgr_image_array: np.array) -> List[np.array]:
    """
    This function detects the contours of tables in an image.

    It does so by detecting horizontal and vertical lines in the image and combining them to form a mask.
    The contours of the mask are then extracted and filtered based on area to identify the tables.
    It also filters out contours that are contained within other contours to avoid detecting
    cells as tables.

    The function uses a point-based containment check to ensure accuracy, where a contour
    is considered "inside" another if most of its points fall within the area of the larger contour.

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
    log.debug(f"Threshold image shape: {thresh.shape}")

    # Detect horizontal lines
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
    detect_horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
    log.debug(f"Horizontal lines shape: {detect_horizontal.shape}")

    # Detect vertical lines
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    detect_vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
    log.debug(f"Vertical lines shape: {detect_vertical.shape}")

    # Combine horizontal and vertical lines to form a mask
    table_mask = cv2.addWeighted(detect_horizontal, 0.5, detect_vertical, 0.5, 0.0)
    log.debug(f"Table mask shape: {table_mask.shape}")

    # Find the contours of the mask
    contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # First filter based on area size
    min_area = 10000  # Minimum area in pixels
    potential_tables = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]

    # Sort by area (largest first) to prioritize larger tables in containment check
    potential_tables.sort(key=cv2.contourArea, reverse=True)

    # Filter out contours that are contained within other contours
    final_tables = []
    for i, cnt1 in enumerate(potential_tables):
        area1 = cv2.contourArea(cnt1)
        is_contained = False

        for j, cnt2 in enumerate(potential_tables):
            if i == j:  # Skip self-comparison
                continue

            area2 = cv2.contourArea(cnt2)

            # Only check if the current contour might be inside a larger one
            if area1 < area2:
                # Create a mask for the potentially larger contour
                mask = np.zeros(bgr_image_array.shape[:2], dtype=np.uint8)
                cv2.drawContours(mask, [cnt2], 0, 255, -1)  # Fill the contour

                # Check what percentage of cnt1 points are inside cnt2
                inside_points = 0
                total_points = len(cnt1)

                for point in cnt1:
                    x, y = point[0]
                    if 0 <= y < mask.shape[0] and 0 <= x < mask.shape[1] and mask[y, x] > 0:
                        inside_points += 1

                # If most points (>50%) of cnt1 are inside cnt2, consider it contained
                if inside_points / total_points > 0.5:
                    is_contained = True
                    log.debug(f"Contour {i} is contained within contour {j} ({inside_points}/{total_points} points inside)")
                    break

        # Only add contours that aren't contained within others
        if not is_contained:
            final_tables.append(cnt1)

    # Log the contours if log level is set to debug
    if log.getEffectiveLevel() < 20:
        log.debug(f"Number of potential tables detected: {len(potential_tables)}")
        log.debug(f"Number of final tables after containment check: {len(final_tables)}")
        for cnt in final_tables:
            log.debug(f"Table contour area: {cv2.contourArea(cnt)}")

    return final_tables


def _is_contour_inside(cnt1, cnt2, img_shape, threshold=0.9):
    """
    Helper function to check if contour cnt1 is inside contour cnt2.
    Uses a pixel-based approach to check what percentage of cnt1's points lie inside cnt2.

    :param cnt1: First contour (potentially inside)
    :param cnt2: Second contour (potentially containing)
    :param img_shape: Shape of the image (height, width)
    :param threshold: Percentage threshold for containment (default: 0.9)
    :return: True if cnt1 is inside cnt2, False otherwise
    """
    # Create a mask for the potentially larger contour
    mask = np.zeros(img_shape, dtype=np.uint8)
    cv2.drawContours(mask, [cnt2], 0, 255, -1)  # Fill the contour

    # Check what percentage of cnt1 points are inside cnt2
    inside_points = 0
    total_points = len(cnt1)

    for point in cnt1:
        x, y = point[0]
        if 0 <= y < mask.shape[0] and 0 <= x < mask.shape[1] and mask[y, x] > 0:
            inside_points += 1

    # If most points of cnt1 are inside cnt2, consider it contained
    return inside_points / total_points > threshold


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
    #_, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        15,  # Size of the neighborhood considered for thresholding (should be an odd number)
        10   # A constant subtracted from the mean (adjusts sensitivity)
    )

    # Detect horizontal lines
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 1))
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
    min_row_height = max(10, gray.shape[0] * 0.03)  # At least 3% of table height or 10px

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


def signature(image, signature_regions=None):
    """
    Detect if a signature is present in the specified regions of an image.

    :param image: The image to check for signatures (numpy array)
    :param signature_regions: Optional list of tuples [(x, y, w, h)] defining signature areas
                            If None, will attempt to detect likely signature areas
    :return: Boolean indicating if a signature is detected
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # If no regions specified, try to detect potential signature areas
    if signature_regions is None:
        signature_regions = _detect_potential_signature_regions(gray)

    # If still no regions found, use default regions based on document proportions
    if not signature_regions:
        h, w = gray.shape
        # Default signature regions - adjust based on your document layout
        # Bottom right corner - common signature area
        signature_regions = [(w//2, 3*h//4, w//2, h//4)]

    # Check each region for signature characteristics
    for region in signature_regions:
        x, y, w, h = region

        # Extract the region
        roi = gray[y:y+h, x:x+w]

        # Apply threshold to identify pen marks
        _, binary = cv2.threshold(roi, 200, 255, cv2.THRESH_BINARY_INV)

        # Calculate pixel density
        pixel_density = np.count_nonzero(binary) / binary.size

        # Calculate contour characteristics
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Filter small noise contours
        significant_contours = [c for c in contours if cv2.contourArea(c) > 20]

        # Combined heuristics
        if (pixel_density > 0.01 and  # Adjust threshold as needed
                len(significant_contours) >= 3):

            return True

    return False


def _detect_potential_signature_regions(gray_image):
    """
    Detect potential signature regions by finding horizontal lines that might be
    signature lines and looking above them.

    :param gray_image: Grayscale image
    :return: List of rectangles [(x, y, w, h)] representing potential signature areas
    """
    h, w = gray_image.shape
    regions = []

    # Detect horizontal lines
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (int(w/15), 1))
    horizontal = cv2.morphologyEx(gray_image, cv2.MORPH_OPEN, horizontal_kernel, iterations=1)
    _, thresh_h = cv2.threshold(horizontal, 200, 255, cv2.THRESH_BINARY_INV)

    # Find contours of horizontal lines
    contours, _ = cv2.findContours(thresh_h, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Sort by Y position (bottom-up)
    contours = sorted(contours, key=lambda c: cv2.boundingRect(c)[1], reverse=True)

    # Check the bottom-most lines
    for i, contour in enumerate(contours[:5]):  # Check only top 5 lines from bottom
        x, y, w_line, h_line = cv2.boundingRect(contour)

        # Only consider lines in the bottom half of the page
        if y > h/2 and w_line > w/4:  # Line is at least 1/4 of page width
            # Define signature region above the line
            sig_height = int(h/10)  # Adjust height of signature area
            sig_y = max(0, y - sig_height)

            regions.append((x, sig_y, w_line, sig_height))

    return regions


def date_present(image, date_regions=None):
    """
    Detect if any handwritten content is present in the expected date area of an image.
    This function checks for the presence of content rather than verifying it's a valid date.

    :param image: The image to check for date content (numpy array)
    :param date_regions: Optional list of tuples [(x, y, w, h)] defining date areas.
     If None, will use default regions based on document layout.
    :return: Boolean indicating if content is detected in the date area
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # If no regions specified, use default regions based on document proportions
    if date_regions is None:
        h, w = gray.shape
        # For the document example provided, date appears in bottom left
        # Adjust these coordinates based on your specific document layout
        date_regions = [(0, 3*h//4, w//3, h//4)]

    # Check each region for any handwritten content
    for region in date_regions:
        x, y, w, h = region

        # Ensure region is within bounds
        x = max(0, x)
        y = max(0, y)
        w = min(w, gray.shape[1] - x)
        h = min(h, gray.shape[0] - y)

        # Extract the region
        roi = gray[y:y+h, x:x+w]

        # Apply threshold to identify pen marks
        _, binary = cv2.threshold(roi, 200, 255, cv2.THRESH_BINARY_INV)

        # Calculate pixel density - key indicator of handwritten content
        pixel_density = np.count_nonzero(binary) / binary.size

        # Count non-trivial contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        significant_contours = [c for c in contours if cv2.contourArea(c) > 10]

        # We only care if there's ANY significant content in the date area
        # Lowered density threshold and contour requirements
        if pixel_density > 0.003 and len(significant_contours) >= 2:
            return True

    return False


def detect_document_completeness(image):
    """
    Check if a document is complete with both signature and date.

    :param image: The document image to check
    :return: Dictionary with completeness status
    """
    has_signature = signature(image)
    has_date = date_present(image)

    return {
        'has_signature': has_signature,
        'has_date': has_date,
        'is_complete': has_signature and has_date
    }
