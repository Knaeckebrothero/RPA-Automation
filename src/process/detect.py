"""
This module contains functions for detecting certain objects in images.
"""
import cv2
import numpy as np
from typing import List, Tuple
import logging as log


def tables(bgr_image_array: np.array) -> List[np.array]:
    """
    This function detects the contours of tables in an image.

    It does so by detecting horizontal and vertical lines in the image and combining them to form a mask.
    The contours of the mask are then extracted and filtered based on area to identify the tables.

    :param bgr_image_array: A NumPy array representing the input image in BGR format.
    :return: A list of points representing the contours of the detected tables.
    """
    grey_bgr_image_array = cv2.cvtColor(bgr_image_array, cv2.COLOR_BGR2GRAY)
    log.debug("Grey image shape:", grey_bgr_image_array.shape)

    # Create a binary threshold (basically splitting the image into two colors of maximum intensity)
    thresh = cv2.adaptiveThreshold(
        grey_bgr_image_array,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        15,  # Size of the neighborhood considered for thresholding (should be an odd number)
        10   # A constant subtracted from the mean (adjusts sensitivity)
    )
    log.debug("Thresholded image shape:", thresh.shape)

    # Detect horizontal lines
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
    detect_horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
    log.debug("Horizontal lines shape:", detect_horizontal.shape)

    # Detect vertical lines
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    detect_vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
    log.debug("Vertical lines shape:", detect_vertical.shape)

    # Combine horizontal and vertical lines to form a mask
    table_mask = cv2.addWeighted(detect_horizontal, 0.5, detect_vertical, 0.5, 0.0)
    log.debug("Table mask shape:", table_mask.shape)

    # Find the contours of the mask and filter based on area size
    contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    table_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > 5000]
    log.debug("Table contours:", table_contours)

    return table_contours


def rows(bgr_image_array: np.array) -> List[Tuple[int, int]]:
    """
    This function detects the row separators in a table image.

    It does so by detecting horizontal lines in the image and extracting the y-coordinates of the bounding rectangles.
    The y-coordinates are then sorted and returned as a list of tuples representing the row separators.

    :param bgr_image_array: A NumPy array representing the input image in BGR format.
    :return: A list of tuples representing the y-coordinates of the detected row separators.
    """
    table_rows = []
    grey_bgr_image_array = cv2.cvtColor(bgr_image_array, cv2.COLOR_BGR2GRAY)
    log.debug("Grey image shape:", grey_bgr_image_array.shape)

    # Create a binary threshold
    _, thresh = cv2.threshold(grey_bgr_image_array, 240, 255, cv2.THRESH_BINARY_INV)
    log.debug("Thresholded image shape:", thresh.shape)

    # Detect horizontal lines (potential row separators)
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    detect_horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
    log.debug("Horizontal lines shape:", detect_horizontal.shape)

    # Find contours of horizontal lines
    contours, _ = cv2.findContours(detect_horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    log.debug("Contours:", contours)

    # Sort contours by y-coordinate of the bounding rectangle (top-left corner)
    contours = sorted(contours, key=lambda c: cv2.boundingRect(c)[1])
    log.debug("Sorted contours:", contours)

    # Extract row coordinates from the contours (y-coordinate of the bounding rectangle)
    for i in range(len(contours) - 1):
        y1 = cv2.boundingRect(contours[i])[1]
        y2 = cv2.boundingRect(contours[i + 1])[1]
        table_rows.append((y1, y2))
        log.debug("Row coordinates:", (y1, y2))

    log.debug("Table rows:", table_rows)

    return table_rows


def cells(bgr_image_array: np.array) -> List[Tuple[int, int]]:
    """
    This function detects the cell boundaries in a row of a table image.

    It does so by detecting vertical lines in the image and extracting the x-coordinates of the bounding rectangles.
    The x-coordinates are then sorted and returned as a list of tuples representing the cell boundaries.
    If no vertical separators are found, the whole row is treated as a single cell.

    :param bgr_image_array: A NumPy array representing the input image in BGR format.
    :return: A list of tuples representing the x-coordinates of the detected cell boundaries.
    """
    if bgr_image_array is None or bgr_image_array.size == 0:
        log.error("Invalid image array provided.")
        return [] # Return an empty list if the image is invalid to avoid errors

    # Variables
    row_cells = []
    prev_x = 0  # Previous x-coordinate of a detected vertical line (used to mark the start of a cell)
    zoom_offset = 5  # Amount to trim off each side of a detected cell (to remove surrounding lines)
    zoom_offset_y = 5  # Amount to trim off the top and bottom of the row (y-axis)
    # TODO: Fix the y axis offset since it is not working as expected
    grey_bgr_image_array = cv2.cvtColor(bgr_image_array, cv2.COLOR_BGR2GRAY)
    log.debug("Image converted to grayscale")

    # Apply cropping to remove lines at the top and bottom of the row (y-axis)
    row_start = zoom_offset_y
    row_end = bgr_image_array.shape[0] - zoom_offset_y

    # Ensure start is less than end to avoid negative height errors
    if row_start < row_end:
        # Crop top and bottom to remove lines at the edges
        cut_bgr_image_array = bgr_image_array[row_start:row_end, :]
        log.debug("Image cropped to remove top and bottom lines.")
    else:
        cut_bgr_image_array = bgr_image_array
        log.debug("No cropping applied to the image.")

    # Create a binary threshold
    _, thresh = cv2.threshold(grey_bgr_image_array, 240, 255, cv2.THRESH_BINARY_INV)
    log.debug("Created binary threshold")

    # Detect vertical lines (potential cell separators)
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 20))
    detect_vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
    log.debug("Detected vertical lines")

    # Find and sort contours of vertical lines by x-coordinate
    contours, _ = cv2.findContours(detect_vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=lambda c: cv2.boundingRect(c)[0])
    log.debug("Sorted contours")

    if len(contours) == 0:
        # If no vertical separators are found, treat the whole row as a single cell
        row_cells.append((max(0, 5), max(0, cut_bgr_image_array.shape[1] - 5)))  # Slight zoom-in to remove edges
        log.debug("No vertical separators found. Treating row as a single cell.")
    else:
        log.debug("Vertical separators detected")

        # Loop through the detected contours and add cell boundaries (x-coordinates)
        for contour in contours:
            # Extract x-coordinate and width of the bounding rectangle
            x, _, w, _ = cv2.boundingRect(contour)

            # Ignore very close lines (to avoid confusing text characters as vertical lines)
            if x - prev_x > 10:
                log.debug("Cell boundary's detected")

                # Adjust the vertical cell boundaries to zoom in slightly (remove surrounding lines)
                cell_start = max(prev_x + zoom_offset, 0)
                cell_end = min(x - zoom_offset, cut_bgr_image_array.shape[1])
                log.debug("Cell boundary's adjusted")

                # Ensure start is less than the end to avoid negative width errors
                if cell_start < cell_end:
                    row_cells.append((cell_start, cell_end))
                    log.debug("Cell boundary's added")

                # Update the previous x-coordinate for the next cell
                prev_x = x + w
                log.debug("Updated previous x-coordinate")

        # Add the last cell (after the last detected vertical line)
        last_cell_start = prev_x + zoom_offset
        last_cell_end = cut_bgr_image_array.shape[1] - zoom_offset

        # Ensure start is less than end for the last cell to avoid negative width errors
        if last_cell_start < last_cell_end:
            row_cells.append((last_cell_start, last_cell_end))
            log.debug("Last cell boundary added")

    return row_cells
