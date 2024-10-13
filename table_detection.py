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
import src.preprocessing.detect as dtct


def detect_table_type(table_image):
    gray = cv2.cvtColor(table_image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

    # Detect vertical lines
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, table_image.shape[0] // 3))
    detect_vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=2)

    # Find contours of vertical lines
    contours, _ = cv2.findContours(detect_vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # If we detect more than one vertical line, it's a multi-column table
    if len(contours) > 1:
        return "multi-column"
    else:
        return "single-column"


def process_single_column_row(row_image):
    # Use the entire row as one cell
    text = ocr_cell(row_image)
    return [text]


def process_multi_column_row(row_image):
    # Split the row into two parts (left and right)
    mid = row_image.shape[1] // 2
    left_part = row_image[:, :mid]
    right_part = row_image[:, mid:]

    # OCR both parts
    left_text = ocr_cell(left_part)
    right_text = ocr_cell(right_part)

    return [left_text, right_text]


def structure_table_data(table_data):
    # Assume first row is header
    header = table_data[0]

    # Structure data
    structured_data = []
    for row in table_data[1:]:
        if len(row) == len(header):
            structured_row = dict(zip(header, row))
            structured_data.append(structured_row)

    return structured_data


# File upload
pdf_document = st.file_uploader(label="", type=["pdf"])
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
        table_contours = dtct.tables(bgr_image)

        # Visualize detected tables
        result_image = bgr_image.copy()
        cv2.drawContours(result_image, table_contours, -1, (0, 255, 0), 3)

        # Display original and processed images (keep your existing display code)
        st.image(image, caption=f"Original - Page {i + 1}", use_column_width=False, width=500)
        st.image(cv2.cvtColor(result_image, cv2.COLOR_BGR2RGB),
                 caption=f"Detected Tables - Page {i + 1}",
                 use_column_width=False, width=500)

        st.write(f"Number of tables detected on page {i + 1}: {len(table_contours)}")
