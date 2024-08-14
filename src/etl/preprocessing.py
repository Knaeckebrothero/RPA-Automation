"""
This module holds methods to preprocess the data.
"""
import cv2
import numpy as np
from pdf2image import convert_from_bytes


def get_images_from_pdf(pdf_bytes: bytes) -> list[np.ndarray]:
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
