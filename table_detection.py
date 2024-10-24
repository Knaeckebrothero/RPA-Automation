"""
This script is using Streamlit to create a user interface.
https://docs.streamlit.io/develop/quick-reference/cheat-sheet

Pdf2Image requires poppler to be installed on the system.
https://pdf2image.readthedocs.io/en/latest/installation.html
"""
import streamlit as st
import cv2
import numpy as np
from pdf2image import convert_from_bytes
import src.preprocessing.detect as dct
from src.preprocessing.ocr import ocr_cell
from typing import List, Tuple


def test_cells(row_image: np.array) -> List[Tuple[int, int]]:
    """
    Detect the boundaries of individual cells in a row of a table.

    :param row_image: A NumPy array representing the row image in BGR format.

    :return: A list of tuples representing the x-coordinates of the detected cell boundaries.
    """
    # Convert row image to grayscale
    if row_image is None or row_image.size == 0:
        return []  # Return an empty list if the image is invalid

    gray = cv2.cvtColor(row_image, cv2.COLOR_BGR2GRAY)

    # Apply binary threshold
    _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

    # Detect vertical lines (potential cell separators)
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 20))
    detect_vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=2)

    # Find contours of vertical lines
    contours, _ = cv2.findContours(detect_vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Sort contours by x-coordinate
    contours = sorted(contours, key=lambda c: cv2.boundingRect(c)[0])

    # Initialize cell boundaries
    cells = []
    prev_x = 0
    zoom_offset = 5  # Amount to trim off each side of a detected cell

    if len(contours) == 0:
        # If no vertical separators are found, treat the row as potentially multiple cells based on horizontal gaps
        cells = test_detect_cells_based_on_horizontal_spacing(thresh)
    else:
        # Loop through the detected contours and add cell boundaries
        for contour in contours:
            x, _, w, _ = cv2.boundingRect(contour)
            if x - prev_x > 10:  # Ignore very close lines
                # Adjust the cell boundaries to zoom in slightly (remove surrounding lines)
                cell_start = max(prev_x + zoom_offset, 0)
                cell_end = min(x - zoom_offset, row_image.shape[1])

                # Ensure start is less than end
                if cell_start < cell_end:
                    cells.append((cell_start, cell_end))

                prev_x = x + w

        # Add the last cell (after the last detected vertical line)
        last_cell_start = prev_x + zoom_offset
        last_cell_end = row_image.shape[1] - zoom_offset

        # Ensure start is less than end for the last cell
        if last_cell_start < last_cell_end:
            cells.append((last_cell_start, last_cell_end))

    # Debug: Print cell boundaries
    for cell in cells:
        print("Cell boundaries:", cell)

    return cells

def test_detect_cells_based_on_horizontal_spacing(thresh_image: np.array) -> List[Tuple[int, int]]:
    """
    Detect the boundaries of individual cells in a row based on horizontal spacing.

    :param thresh_image: A binary thresholded image (inverted) of the row.

    :return: A list of tuples representing the x-coordinates of the detected cell boundaries.
    """
    # Calculate the vertical projection profile (sum of pixel values for each column)
    projection = np.sum(thresh_image, axis=0)

    # Define minimum gap threshold for detecting cell separation
    gap_threshold = 10  # Adjust as needed to match spacing in the row
    min_gap_width = 20  # Minimum width of a gap to be considered as cell separator

    cells = []
    in_gap = False
    start_index = 0

    for x in range(len(projection)):
        if projection[x] <= gap_threshold:  # Column with minimal or no content (gap)
            if not in_gap:
                # Starting a new gap
                in_gap = True
                start_index = x
        else:
            if in_gap:
                # Ending a gap
                in_gap = False
                gap_width = x - start_index
                if gap_width > min_gap_width:
                    # Add a new cell boundary
                    cells.append((start_index, x))

    # If the entire row is detected as a single segment, treat the whole row as a cell
    if len(cells) == 0:
        cells.append((5, thresh_image.shape[1] - 5))

    return cells


# File upload
pdf_document = st.file_uploader(label="Upload PDF here", type=["pdf"])
if pdf_document is not None:
    images = convert_from_bytes(pdf_document.read())
    st.image(images, width=350) # use_column_width="auto"


    ### Test code goes here ###
    for i, image in enumerate(images):

        # Convert the image to a NumPy array (shape is height times width times RGB channels)
        np_image = np.array(image)

        # Convert to BGR format since it is required for OpenCV (BGR is basically RGB reversed)
        bgr_image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)

        # Detect tables
        table_contours = dct.tables(bgr_image)

        # Visualize detected tables
        #result_image = bgr_image.copy()
        #cv2.drawContours(result_image, table_contours, -1, (0, 255, 0), 3)
        #st.image(image, caption=f"Original - Page {i + 1}", use_column_width=False, width=350)
        #st.image(cv2.cvtColor(result_image, cv2.COLOR_BGR2RGB),
        #         caption=f"Detected Tables - Page {i + 1}",
        #         use_column_width=False, width=350)
        #st.write(f"Number of tables detected on page {i + 1}: {len(table_contours)}")

        # Process each detected table
        for j, contour in enumerate(table_contours):
            table_data = []
            x, y, w, h = cv2.boundingRect(contour)
            table_roi = bgr_image[y:y + h, x:x + w]

            # Visualize the cutout tables
            st.image(cv2.cvtColor(table_roi, cv2.COLOR_BGR2RGB),
                     caption=f"Table {j + 1}",
                     use_column_width=False, width=500)

            # Detect rows in the table
            rows = dct.rows(table_roi)
            #st.write(f"Number of rows detected: {len(rows)}")

            # Process each detected row
            for k, (y1, y2) in enumerate(rows):
                row_image = table_roi[y1:y2, :]
                row_data = []
                #st.image(cv2.cvtColor(row_image, cv2.COLOR_BGR2RGB),
                #         caption=f"Row {k + 1}",
                #         use_column_width=True)

                # Detect cells in the row
                cells = dct.cells(row_image)

                for m, (x1, x2) in enumerate(cells):
                    cell_image = row_image[:, x1:x2]

                    st.image(cv2.cvtColor(cell_image, cv2.COLOR_BGR2RGB),
                             caption=f"Cell",
                             use_column_width=False, width=350)

                    cell_text = ocr_cell(cell_image)
                    row_data.append(cell_text)

                table_data.append(row_data)

            # Display extracted data in a Streamlit table
            st.write("Extracted Table Data:")
            st.table(table_data)
            st.write("---")
