"""
This module contains functions for detecting certain objects in images.
"""
import numpy as np
import cv2
from typing import List


def tables(bgr_image_array: np.array) -> List[np.array]:
    """
    Detect the contours of tables based on horizontal and vertical lines.

    :param bgr_image_array: A NumPy array representing the input image in BGR format.

    :return: A list of points representing the contours of the detected tables.
    """

    # Convert to grayscale
    grey_bgr_image_array = cv2.cvtColor(bgr_image_array, cv2.COLOR_BGR2GRAY)

    # Create a binary threshold (basically splitting the image into two colors of maximum intensity)
    # _, thresh = cv2.threshold(grey_bgr_image_array, 240, 255, cv2.THRESH_BINARY_INV)
    thresh = cv2.adaptiveThreshold(
        grey_bgr_image_array,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        15,  # Block size - size of the neighborhood considered for thresholding (should be an odd number)
        10   # Constant subtracted from the mean, adjusts sensitivity
    )

    # Detect horizontal lines
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    detect_horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)

    # Detect vertical lines
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    detect_vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=2)

    # Combine horizontal and vertical lines
    table_mask = cv2.addWeighted(detect_horizontal, 0.5, detect_vertical, 0.5, 0.0)

    # Find contours
    contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter contours based on area (adjust as needed)
    min_area = 5000  # Minimum area to be considered a table
    table_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]

    return table_contours
