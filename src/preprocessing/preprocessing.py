"""
This module holds methods to preprocess the data.
"""
import cv2
import numpy as np
from pdf2image import convert_from_bytes


def get_bgr_images_from_pdf(pdf_bytes: bytes) -> list[np.ndarray]:
    """
    Convert a pdf file to a list of images. Each page in the pdf is converted to an image.
    The images are stored as numpy arrays and are converted to BGR format.
    BGR format is used as OpenCV uses BGR format for images.
    It is essentially RGB with the channels reversed.

    :param pdf_bytes: The pdf file as bytes.
    :return: A list of numpy arrays representing the images.
    """
    images = []

    # Convert all the pages into bgr images and append them to the list
    for image in convert_from_bytes(pdf_bytes):
        np_image = np.array(image)
        bgr_image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)
        images.append(bgr_image)

    return images


def detect_tables(bgr_image_array: np.ndarray) -> list[np.ndarray]:
    """
    Detect tables in an image and return the contours of the tables if found.
    If no tables are found, an empty list is returned.

    The function first converts the image to grayscale and then applies a binary threshold.
    It then detects horizontal and vertical lines in the image using morphological operations.
    The horizontal and vertical lines are combined to create a mask of the table.
    Contours are then found in the mask, and contours with an area greater than a threshold are considered tables.

    The function expects the input image to be in BGR format.

    :param bgr_image_array: A numpy array representing the image.
    :return: Returns a list of numpy arrays representing the contours of the tables.
    """
    # Convert to grayscale
    gray = cv2.cvtColor(bgr_image_array, cv2.COLOR_BGR2GRAY)

    # Binary threshold
    _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

    # Detect horizontal lines
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    detect_horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)

    # Detect vertical lines
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    detect_vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)

    # Combine horizontal and vertical lines
    table_mask = cv2.addWeighted(detect_horizontal, 0.5, detect_vertical, 0.5, 0.0)

    # Find contours
    contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter contours based on area with a minimum area of 5000
    min_area = 5000
    table_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]

    return table_contours


def detect_rows(table_image, table_contour):
    """
    This function detects rows in a table image.

    :param table_image:
    :param table_contour:
    :return:
    """

    # Extract table region
    x, y, w, h = cv2.boundingRect(table_contour)

    # Extract the table region
    table_roi = table_image[y:y + h, x:x + w]

    # Convert to grayscale
    gray = cv2.cvtColor(table_roi, cv2.COLOR_BGR2GRAY)

    # Binary threshold
    _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

    # Detect horizontal lines (potential row separators)
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    detect_horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)

    # Find contours of horizontal lines
    contours, _ = cv2.findContours(detect_horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Sort contours by y-coordinate
    contours = sorted(contours, key=lambda c: cv2.boundingRect(c)[1])

    # Extract row coordinates
    rows = []
    for i in range(len(contours) - 1):
        y1 = cv2.boundingRect(contours[i])[1]
        y2 = cv2.boundingRect(contours[i + 1])[1]
        rows.append((y1, y2))

    return rows


def detect_cells(row_image):
    gray = cv2.cvtColor(row_image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

    # Detect vertical lines (potential cell separators)
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 20))
    detect_vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=2)

    # Find contours of vertical lines
    contours, _ = cv2.findContours(detect_vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Sort contours by x-coordinate
    contours = sorted(contours, key=lambda c: cv2.boundingRect(c)[0])

    # Extract cell coordinates
    cells = []
    prev_x = 0
    for contour in contours:
        x, _, w, _ = cv2.boundingRect(contour)
        if x - prev_x > 10:  # Ignore very close lines
            cells.append((prev_x, x))
            prev_x = x + w
    cells.append((prev_x, row_image.shape[1]))  # Add last cell

    return cells

