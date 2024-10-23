"""
This module contains functions for detecting certain objects in images.
"""
import numpy as np
import cv2
from typing import List

# TEST
import streamlit as st

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
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
    detect_horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)

    # Detect vertical lines
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    detect_vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=2)

    # Combine horizontal and vertical lines
    table_mask = cv2.addWeighted(detect_horizontal, 0.5, detect_vertical, 0.5, 0.0)

    # Find contours
    contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter contours based on area
    min_area = 5000
    table_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]

    return table_contours


def rows(table_image):
    gray = cv2.cvtColor(table_image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

    # Detect horizontal lines (potential row separators)
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    detect_horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)

    # Find contours of horizontal lines
    contours, _ = cv2.findContours(detect_horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Sort contours by y-coordinate
    contours = sorted(contours, key=lambda c: cv2.boundingRect(c)[1])

    # Extract row coordinates
    tbl_rows = []
    for i in range(len(contours) - 1):
        y1 = cv2.boundingRect(contours[i])[1]
        y2 = cv2.boundingRect(contours[i + 1])[1]
        tbl_rows.append((y1, y2))

    return tbl_rows


def cells(row_image):
    gray = cv2.cvtColor(row_image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
    cells = []

    # Detect vertical lines (potential cell separators)
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 20))
    detect_vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=2)

    # Find contours of vertical lines
    contours, _ = cv2.findContours(detect_vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Sort contours by x-coordinate
    contours = sorted(contours, key=lambda c: cv2.boundingRect(c)[0])

    prev_x = 0
    for contour in contours:
        x, _, w, _ = cv2.boundingRect(contour)
        if x - prev_x > 10:  # Ignore very close lines
            cells.append((prev_x, x))
            prev_x = x + w

        print("Cell: ", (prev_x, row_image.shape[1]))
        # TODO: Fix cell issues!

    # Add last cell
    cells.append((prev_x, row_image.shape[1]))
    # print("Cell: ", (prev_x, row_image.shape[1]))

    return cells
