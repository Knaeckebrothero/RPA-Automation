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
    Normalizes the resolution of the given image to the specified target DPI by resizing the image based
    on its estimated DPI. If the image's estimated DPI matches the target DPI, the image is returned
    unaltered. Otherwise, the function rescales the image dimensions proportionally to match the desired
    DPI.

    :param image: The input image to be normalized.
    :type image: numpy.ndarray
    :param target_dpi: The desired DPI (dots per inch) to which the image should be normalized.
                       Defaults to 400 if not specified.
    :type target_dpi: int, optional
    :return: The image resized to the target DPI if necessary, or the unaltered image otherwise.
    :rtype: numpy.ndarray
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
    Estimates the dots per inch (DPI) of an image or screen based on its dimensions
    (height and width). It assumes the document is of A4 size, where the longest
    dimension is typically used for portrait orientation (11.69 inches). The function
    calculates the DPI by dividing the longest dimension by the longest inch of an
    A4 document. The result is clamped within a reasonable range (75-1200), where
    the lower and upper bounds represent typical minimum and maximum DPI values.

    :param height: The height of the image or screen in pixels.
    :type height: int
    :param width: The width of the image or screen in pixels.
    :type width: int
    :return: The estimated DPI clamped within the range of 75 and 1200.
    :rtype: float
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
    Detects and extracts potential table regions from a given image represented as a
    NumPy array. The function processes the input image to identify horizontal and
    vertical lines, combines them to form a mask, and then detects contours that
    correspond to possible table regions. It performs filtering based on area and
    containment rules to refine the detected table regions.

    Tables are identified based on structural cues such as horizontal and
    vertical lines, followed by contour detection and analysis.

    :param bgr_image_array: Input image in BGR color format or grayscale. A 3-dimensional array
        is assumed as a color image, which will be converted into grayscale internally for
        further processing. Grayscale images are processed directly.
    :type bgr_image_array: np.array

    :return: A list of NumPy arrays representing the contours of detected table regions.
        Each contour describes the boundary of a potential table in the input image.
    :rtype: List[np.array]
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
    Determines if one contour is mostly contained within another contour based
    on a specified threshold. The function evaluates the percentage of points
    from the smaller contour that are inside the larger contour. If this
    percentage exceeds the given threshold, the smaller contour is considered
    to be inside the larger contour. The function uses a binary mask to aid
    in the calculation.

    :param cnt1: The smaller contour whose points will be checked for containment.
        The contour should be a list or array of points.
    :type cnt1: list or numpy.ndarray

    :param cnt2: The potentially larger contour within which the points of `cnt1`
        will be tested for containment. The contour should be a list or array of
        points.
    :type cnt2: list or numpy.ndarray

    :param img_shape: The shape of the binary mask used for containment testing.
        Should typically be `(height, width)` of the image from which contours
        were extracted.
    :type img_shape: tuple

    :param threshold: The minimum percentage (0-1) of `cnt1` points required
        to be inside `cnt2` for `cnt1` to be considered contained. Default is
        0.9 (90%).
    :type threshold: float

    :return: A boolean indicating whether the smaller contour (`cnt1`) is
        considered contained within the larger contour (`cnt2`) based on the
        threshold.
    :rtype: bool
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
    Extracts the row boundaries from an image of a table by detecting horizontal lines.
    The function works with a grayscale image or automatically converts a color image
    to grayscale. Horizontal lines are identified to determine row boundaries, and rows
    are created based on the lines detected. Post-processing is applied to filter out
    insignificant rows and handle edge cases where no lines are detected.

    :param table_image: The input image of the table, expected as a numpy array.
        The image should represent the table from which row boundaries need to be extracted.
    :type table_image: np.array

    :return: A list of tuples representing the start and end vertical positions of the
        detected rows in the table. Each tuple consists of two integers: the start and
        end y-coordinate of a row.
    :rtype: List[Tuple[int, int]]
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
    Extracts cells from a row image by detecting vertical line separators. This function processes
    a given row image and identifies the x-coordinate boundaries of potential "cells" (subsections
    of the row). It uses computer vision techniques, such as contour detection and binary
    thresholding, to determine vertical lines, which serve as separators for the cells.

    :param row_image: Image of a single row from a table, represented as a numpy array. This image
        may be in grayscale or color format.
    :type row_image: np.array
    :return: A list of tuples where each tuple represents the start and end x-coordinates of a cell
        within the row. Each tuple defines the range `(start_x, end_x)` encompassing the cell.
    :rtype: List[Tuple[int, int]]
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
    Extracts a BaFin ID from the given text string.

    The function attempts to find a valid German BaFin (Federal Financial Supervisory Authority)
    identification number (ID), which is an 8-digit numeric value. It employs multiple
    regular expression patterns to detect the ID within the provided text. Keywords and
    context are also examined to identify possible IDs if primary patterns fail.

    :param text: The input text in which the BaFin ID needs to be identified.
    :type text: str
    :return: The extracted BaFin ID as an integer if found, otherwise None.
    :rtype: int | None
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
    Computes the similarity ratio between two sequences.

    This function calculates the similarity ratio between two input sequences
    using the `difflib.SequenceMatcher`. The similarity ratio is a floating-point
    value between 0 and 1, where 1 indicates a perfect match, and values closer
    to 0 indicate less similarity.

    :param a: The first sequence to compare.
    :type a: str
    :param b: The second sequence to compare.
    :type b: str
    :return: The similarity ratio between the two sequences.
    :rtype: float
    """
    return SequenceMatcher(None, a, b).ratio()


def signature(image, signature_regions=None):
    """
    Detects the presence of a signature in an image by analyzing specified or detected
    signature regions. The image is analyzed for features typically found in a signature,
    such as pixel density and contour characteristics. If no regions are specified, the
    function attempts to detect potential signature areas or switches to default signature
    regions based on common document layout.

    :param image: Input image to analyze for signature presence. Can be grayscale or colored.
    :type image: numpy.ndarray
    :param signature_regions: Optional. List of regions (x, y, width, height) to specifically
                               analyze for signature presence. If not provided, signature regions
                               are detected automatically or default regions are used.
    :type signature_regions: list[tuple[int, int, int, int]] | None
    :return: Indicates whether a signature is present in the analyzed regions of the image.
    :rtype: bool
    """
    if len(image.shape) == 3:
        # Convert to grayscale if needed
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        log.debug("Converted image to grayscale")
    else:
        # Continue if not
        gray = image
        log.debug("Image already grayscale")

    # Normalize the image
    gray_normalized = normalize_image_resolution(gray)

    # If no regions specified, try to detect potential signature areas
    if signature_regions is None:
        signature_regions = _detect_potential_signature_regions(gray_normalized)
        log.debug(f"Detected {len(signature_regions)} potential signature areas")

    # If still no regions found, use default regions based on document proportions
    if not signature_regions:
        h, w = gray_normalized.shape
        # Default signature regions - adjust based on your document layout
        # Bottom right corner - common signature area
        signature_regions = [(w//2, 3*h//4, w//2, h//4)]

    # Check each region for signature characteristics
    for region in signature_regions:
        x, y, w, h = region

        # Extract the region
        roi = gray_normalized[y:y+h, x:x+w]

        # Apply threshold to identify pen marks
        _, binary = cv2.threshold(roi, 200, 255, cv2.THRESH_BINARY_INV)

        # Calculate pixel density
        pixel_density = np.count_nonzero(binary) / binary.size

        # Calculate contour characteristics
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Filter small noise contours
        significant_contours = [c for c in contours if cv2.contourArea(c) > 20]

        # Combined heuristics and adjust threshold as needed
        if pixel_density > 0.01 and len(significant_contours) >= 3:
            return True

    return False


def _detect_potential_signature_regions(gray_image):
    """
    Detects potential signature regions in a grayscale image based on specific
    geometric and positional constraints.

    This function processes the input grayscale image to identify straight
    line segments that are horizontally oriented, situated in the lower
    portion of the image, and fit the expected characteristics of signature
    lines. Detected regions are then adjusted around these line segments to
    define bounding areas that may contain a signature.

    :param gray_image: A single-channel image (grayscale) to analyze for potential
        signature regions.
    :type gray_image: numpy.ndarray
    :return: A list of rectangular regions of interest that may contain
        signatures. Each region is represented by a tuple `(x, y, width,
        height)`, where `x` and `y` specify the top-left corner of the rectangle,
        and `width`, `height` indicate its size.
    :rtype: list[tuple[int, int, int, int]]
    """
    h, w = gray_image.shape
    regions = []

    # 1. Edge Detection
    edges = cv2.Canny(gray_image, 50, 150, apertureSize=3)

    # 2. Hough Line Transform
    # Original parameters threshold=80, minLineLength=int(w/3.5), maxLineGap=int(w/220)
    # Tuned: threshold=80, minLineLength=int(w/2.6), maxLineGap=int(w/50)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80, minLineLength=int(w/3), maxLineGap=int(w/50))

    if lines is not None:
        potential_lines = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            # 3. Filtering Lines
            angle_thresh_degrees = 5
            angle = np.arctan2(y2 - y1, x2 - x1) * 180. / np.pi
            if abs(angle) < angle_thresh_degrees or abs(angle - 180) < angle_thresh_degrees or abs(angle + 180) < angle_thresh_degrees:
                line_y_center = (y1 + y2) / 2
                line_width = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)

                # --- ADJUSTED Y-POSITION CHECK ---
                # Only consider lines in the bottom 25% of the page
                if line_y_center > (3 * h / 4):
                    min_acceptable_width = w / 2.8 #2.65
                    max_acceptable_width = w / 2.2

                    if line_width > min_acceptable_width and line_width < max_acceptable_width:
                        # --- RIGHT SIDE PRIORITIZATION ---
                        # Calculate what percentage of the line is on the right half
                        x_right = max(x1, x2)
                        x_left = min(x1, x2)
                        
                        # Check if either the middle of the field is on the right side
                        # OR more than 50% of the field is on the right side
                        line_middle_x = (x_left + x_right) / 2
                        is_middle_on_right = line_middle_x > (w / 2)
                        
                        # Calculate how much of the line is on the right side
                        if x_right > (w / 2):
                            if x_left < (w / 2):  # Line crosses the middle
                                right_portion = x_right - (w / 2)
                                right_portion_percentage = right_portion / line_width
                            else:  # Line is fully on the right
                                right_portion_percentage = 1.0
                        else:  # Line is fully on the left
                            right_portion_percentage = 0.0
                        
                        # Add to potential lines if it meets our right-side criteria
                        if is_middle_on_right or right_portion_percentage > 0.5:
                            potential_lines.append((min(x1, x2), int(line_y_center), int(line_width), max(1, abs(y2-y1))))

        potential_lines = sorted(potential_lines, key=lambda l: l[1], reverse=True)

        for i, (lx, ly, lw, lh_line) in enumerate(potential_lines):
            sig_height = int(h / 15)
            sig_y = max(0, ly - sig_height)
            regions.append((lx, sig_y, lw, sig_height))

    return regions


def _detect_potential_date_regions(gray_image):
    """
    Detects and extracts potential regions in an image that could correspond to a date field. The function assumes
    that the input image is in grayscale format. It identifies date regions by analyzing horizontal line features
    in the image, which often delimit date fields. Several criteria such as angle, position, and size are utilized
    to filter and detect relevant regions.

    :param gray_image: Input grayscale image to process for detecting potential date regions.
    :type gray_image: numpy.ndarray
    :return: A list of potential bounding boxes likely to contain date information. Each bounding box is represented
             as a tuple (x, y, width, height).
    :rtype: list[tuple[int, int, int, int]]
    """
    h, w = gray_image.shape
    regions = []

    # 1. Edge Detection
    edges = cv2.Canny(gray_image, 50, 150, apertureSize=3)

    # 2. Hough Line Transform
    #lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=120, minLineLength=int(w/6), maxLineGap=int(w/350))
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80, minLineLength=int(w/3), maxLineGap=int(w/50))

    if lines is not None:
        potential_lines = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            # 3. Filtering Lines
            angle_thresh_degrees = 5
            angle = np.arctan2(y2 - y1, x2 - x1) * 180. / np.pi
            if abs(angle) < angle_thresh_degrees or abs(angle - 180) < angle_thresh_degrees or abs(angle + 180) < angle_thresh_degrees:
                line_y_center = (y1 + y2) / 2
                line_x_center = (x1 + x2) / 2

                # --- ADJUSTED Y-POSITION CHECK ---
                # Only consider lines in the bottom 25% of the page
                if line_y_center > (3 * h / 4):
                    # --- ADJUSTED X-POSITION CHECK ---
                    # Only consider lines in the left 50% of the page
                    if line_x_center < (w / 2):
                        line_width = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)

                        # Date lines are typically shorter than signature lines
                        min_acceptable_width = w / 20 # 8
                        max_acceptable_width = w / 5 # 5

                        if line_width > min_acceptable_width and line_width < max_acceptable_width:
                            potential_lines.append((min(x1, x2), int(line_y_center), int(line_width), max(1, abs(y2-y1))))

        potential_lines = sorted(potential_lines, key=lambda l: l[1], reverse=True)

        for i, (lx, ly, lw, lh_line) in enumerate(potential_lines):
            # Date fields are typically smaller than signature fields
            date_height = int(h / 22)
            date_y = max(0, ly - date_height)
            regions.append((lx, date_y, lw, date_height))

    return regions


def date(image, date_regions=None):
    """
    Determines the presence of handwritten content in specific regions of an
    image, primarily aimed at detecting handwritten dates on documents. The
    image is processed, and date regions are either provided or detected
    automatically. Various checks such as pixel density, contours, and region
    validation are performed to identify handwritten content.

    :param image: Input image, either in grayscale or color. If the image is
        in color, it will be converted to grayscale.
    :type image: numpy.ndarray
    :param date_regions: Optional parameter specifying regions of interest
        (ROIs) in the format [(x, y, w, h), ...] to check for handwritten
        content. If not provided, regions will be automatically detected based
        on document layout.
    :type date_regions: list[tuple[int, int, int, int]] | None
    :return: A Boolean value indicating whether significant handwritten
        content is detected in the specified or detected date regions.
    :rtype: bool
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Normalize the image
    gray_normalized = normalize_image_resolution(gray)

    # If no regions specified, try to detect potential date areas
    if date_regions is None:
        date_regions = _detect_potential_date_regions(gray_normalized)
        log.debug(f"Detected {len(date_regions)} potential date areas")

    # If still no regions found, use default regions based on document proportions
    if not date_regions:
        h, w = gray_normalized.shape
        # For the document example provided, date appears in bottom left
        # Adjust these coordinates based on your specific document layout
        date_regions = [(0, 3*h//4, w//3, h//4)]

    # Check each region for any handwritten content
    for region in date_regions:
        x, y, w, h = region

        # Ensure region is within bounds
        x = max(0, x)
        y = max(0, y)
        w = min(w, gray_normalized.shape[1] - x)
        h = min(h, gray_normalized.shape[0] - y)

        # Extract the region
        roi = gray_normalized[y:y+h, x:x+w]

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
    Analyzes an image of a document to determine its completeness, based on the presence
    of a signature and a date. The function inspects the given image for these two key
    elements and returns a dictionary containing the evaluation results.

    :param image: The input image containing the document to analyze.
    :type image: Any
    :return: A dictionary with the completeness assessment results. It includes:
             - 'has_signature': Boolean indicating if a signature is detected.
             - 'has_date': Boolean indicating if a date is detected.
             - 'is_complete': Boolean indicating if the document has both a signature and a date present.
    :rtype: dict
    """
    has_signature = signature(image)
    has_date = date(image)

    return {
        'has_signature': has_signature,
        'has_date': has_date,
        'is_complete': has_signature and has_date
    }
