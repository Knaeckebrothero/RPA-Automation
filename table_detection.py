"""
This script is using Streamlit to create a user interface.
https://docs.streamlit.io/develop/quick-reference/cheat-sheet

Pdf2Image requires poppler to be installed on the system.
https://pdf2image.readthedocs.io/en/latest/installation.html
"""
import streamlit as st
import cv2
import numpy as np
import src.processing.detect as dct
from src.processing.ocr import ocr_cell, create_ocr_reader
from src.processing.files import get_images_from_pdf


# File upload
pdf_document = st.file_uploader(label="Upload PDF here", type=["pdf"])
display_tables = st.checkbox("Show tables")
if pdf_document is not None:
    #images = convert_from_bytes(pdf_document.read())
    images = get_images_from_pdf(pdf_document.read())

    st.image(images, width=350)  # use_column_width="auto"

    ocr_reader = create_ocr_reader(use_gpu=True)

    ### Test code goes here ###
    for i, image in enumerate(images):

        # Convert the image to a NumPy array (shape is height times width times RGB channels)
        np_image_array = np.array(image)

        # Convert to BGR format since it is required for OpenCV (BGR is basically RGB but in reverse)
        bgr_image_array = cv2.cvtColor(np_image_array, cv2.COLOR_RGB2BGR)

        # Detect tables
        table_contours = dct.tables(bgr_image_array)

        st.write(f"Number of tables detected on page {i + 1}: {len(table_contours)}")

        if not display_tables: ### ONLY FOR TESTING ###

            # Process each detected table
            for j, contour in enumerate(table_contours):
                table_data = []
                x, y, w, h = cv2.boundingRect(contour)
                table_roi = bgr_image_array[y:y + h, x:x + w]

                # Visualize the cutout tables
                st.image(cv2.cvtColor(table_roi, cv2.COLOR_BGR2RGB),
                         caption=f"Image: {i + 1}, Table: {j + 1}",
                         use_column_width=False, width=500)

                # Detect rows in the table
                rows = dct.rows(table_roi)
                st.write(f"Number of rows detected: {len(rows)}, Image: {i + 1}, Table: {j + 1}")

                # Process each detected row
                for k, (y1, y2) in enumerate(rows):
                    row_image = table_roi[y1:y2, :]
                    row_data = []
                    st.image(cv2.cvtColor(row_image, cv2.COLOR_BGR2RGB),
                             caption=f"Row {k + 1}",
                             use_column_width=True)

                    # Detect cells in the row
                    cells = dct.cells(row_image)

                    for m, (x1, x2) in enumerate(cells):
                        cell_image = row_image[:, x1:x2]

                        st.image(cv2.cvtColor(cell_image, cv2.COLOR_BGR2RGB),
                                 caption=f"Cell",
                                 use_column_width=False, width=350)

                        # Perform OCR on the cell
                        cell_text = ocr_cell(cell_image, ocr_reader)
                        row_data.append(cell_text)

                    table_data.append(row_data)

                # Display extracted data in a Streamlit table
                st.write("Extracted Table Data:")
                st.table(table_data)

        else:
            ### INSERT FOR DEBUGGING ###
            # Visualize detected tables
            result_image = bgr_image_array.copy()
            cv2.drawContours(result_image, table_contours, -1, (0, 255, 0), 3)
            st.image(image, caption=f"Original - Page {i + 1}", use_column_width=False, width=350)
            st.image(cv2.cvtColor(result_image, cv2.COLOR_BGR2RGB),
                     caption=f"Detected Tables - Page {i + 1}",
                     use_column_width=False, width=350)
            st.write(f"Number of tables detected on page {i + 1}: {len(table_contours)}")
            ### INSERT FOR DEBUGGING ###
