"""
This script is using Streamlit to create a user interface.
https://docs.streamlit.io/develop/quick-reference/cheat-sheet

Pdf2Image requires poppler to be installed on the system.
https://pdf2image.readthedocs.io/en/latest/installation.html
"""
import streamlit as st
import cv2
import numpy as np
import processing.detect as dtct
from processing.ocr import ocr_cell, create_ocr_reader
from processing.files import get_images_from_pdf
from cls.document import PDF


# File upload
pdf_document = st.file_uploader(label="Upload PDF here", type=["pdf"])
display_tables = st.checkbox("Show tables")
display_signatures = st.checkbox("Show signatures")
display_dates = st.checkbox("Show dates")

if pdf_document is not None:
    pdf_content_bytes = pdf_document.read() # Read content once
    images = get_images_from_pdf(pdf_content_bytes)

    st.image(images, width=350)  # use_column_width="auto"

    ocr_reader = create_ocr_reader(use_gpu=True)

    # Instantiate PDF class and determine signature page
    # Assuming PDF class constructor takes content and filename, and sets _signature_page_index via extract_table_data
    # You might need to adjust filename part if not available or not needed by your PDF class
    pdf_doc_object = PDF(content=pdf_content_bytes)
    pdf_doc_object.extract_table_data(ocr_reader=ocr_reader) # This should populate _signature_page_index

    signature_page_idx = pdf_doc_object._signature_page_index if hasattr(pdf_doc_object, '_signature_page_index') else -1
    if signature_page_idx != -1:
        st.info(f"The application logic identified Page {signature_page_idx + 1} as the signature page.")
    else:
        st.warning("Signature page could not be determined by the PDF class logic.")

    ### Test code goes here ###
    for i, image in enumerate(images):
        # Convert the image to a NumPy array
        np_image_array = np.array(image)
        # Convert to BGR format for OpenCV
        bgr_image_array = cv2.cvtColor(np_image_array, cv2.COLOR_RGB2BGR)
        # Normalize image resolution
        bgr_image_array = dtct.normalize_image_resolution(bgr_image_array)

        result_image = bgr_image_array.copy()

        # Always detect tables for consistent data, regardless of display_tables for drawing
        table_contours = dtct.tables(bgr_image_array)

        if display_tables:
            st.write(f"Number of tables detected on page {i + 1}: {len(table_contours)}")
            cv2.drawContours(result_image, table_contours, -1, (0, 255, 0), 3) # Green for tables

        if display_signatures:
            if i == signature_page_idx:
                st.write(f"Attempting to detect signature regions on identified signature Page {i + 1}...")
                # Convert to grayscale for signature detection
                gray_image_array = cv2.cvtColor(bgr_image_array, cv2.COLOR_BGR2GRAY)
                # Detect potential signature regions using the function from detect.py
                signature_regions = dtct._detect_potential_signature_regions(gray_image_array)
                st.write(f"Number of potential signature regions detected: {len(signature_regions)}")

                if not signature_regions:
                    st.write("No signature regions detected by the dynamic function.")
                else:
                    # Visualize detected signature regions
                    for region in signature_regions:
                        x_sig, y_sig, w_sig, h_sig = region # Renamed to avoid conflict with table loop vars
                        cv2.rectangle(result_image, (x_sig, y_sig), (x_sig + w_sig, y_sig + h_sig), (0, 0, 255), 2) # Red for signatures

            elif signature_page_idx != -1 : # Only show if a signature page was determined
                st.write(f"Page {i + 1} is not the identified signature page. Skipping signature detection.")
            # If signature_page_idx is -1, this loop won't execute the main signature logic, which is fine.

        if display_dates:
            if i == signature_page_idx:
                st.write(f"Attempting to detect date regions on identified signature Page {i + 1}...")
                # Convert to grayscale for date detection if not already done
                if 'gray_image_array' not in locals():
                    gray_image_array = cv2.cvtColor(bgr_image_array, cv2.COLOR_BGR2GRAY)
                # Detect potential date regions using the function from detect.py
                date_regions = dtct._detect_potential_date_regions(gray_image_array)
                st.write(f"Number of potential date regions detected: {len(date_regions)}")

                if not date_regions:
                    st.write("No date regions detected by the dynamic function.")
                else:
                    # Visualize detected date regions
                    for region in date_regions:
                        x_date, y_date, w_date, h_date = region # Renamed to avoid conflict with other loop vars
                        cv2.rectangle(result_image, (x_date, y_date), (x_date + w_date, y_date + h_date), (255, 0, 0), 2) # Blue for dates

            elif signature_page_idx != -1 : # Only show if a signature page was determined
                st.write(f"Page {i + 1} is not the identified signature page. Skipping date detection.")
            # If signature_page_idx is -1, this loop won't execute the main date logic, which is fine.

        # Display the original and result images if any detection is enabled
        if display_tables or (display_signatures and i == signature_page_idx and signature_regions) or (display_dates and i == signature_page_idx and 'date_regions' in locals() and date_regions): # Ensure regions were found to display
            st.image(image, caption=f"Original - Page {i + 1}", use_column_width=False, width=350)
            st.image(cv2.cvtColor(result_image, cv2.COLOR_BGR2RGB),
                     caption=f"Detected Areas - Page {i + 1}",
                     use_column_width=False, width=350)
        elif i == 0 and not display_tables and not (display_signatures and i == signature_page_idx) and not (display_dates and i == signature_page_idx): # Show original if nothing else is displayed on first page
            st.image(image, caption=f"Original - Page {i + 1}", use_column_width=False, width=350)


        # Detailed table processing logic
        if not display_tables and table_contours:
            st.write(f"Number of tables detected for processing on page {i + 1}: {len(table_contours)}")
            for j, contour_item in enumerate(table_contours):
                table_data = []
                x_tbl, y_tbl, w_tbl, h_tbl = cv2.boundingRect(contour_item) # Renamed to avoid conflict
                table_roi = bgr_image_array[y_tbl:y_tbl + h_tbl, x_tbl:x_tbl + w_tbl]

                st.image(cv2.cvtColor(table_roi, cv2.COLOR_BGR2RGB),
                         caption=f"Image: {i + 1}, Table: {j + 1}",
                         use_column_width=False, width=500)

                rows = dtct.rows(table_roi)
                st.write(f"Number of rows detected: {len(rows)}, Image: {i + 1}, Table: {j + 1}")

                for k, (y1, y2) in enumerate(rows):
                    row_image = table_roi[y1:y2, :]
                    row_data = []
                    st.image(cv2.cvtColor(row_image, cv2.COLOR_BGR2RGB),
                             caption=f"Row {k + 1}",
                             use_column_width=True)
                    cells = dtct.cells(row_image)
                    for m, (x1, x2) in enumerate(cells):
                        cell_image = row_image[:, x1:x2]
                        st.image(cv2.cvtColor(cell_image, cv2.COLOR_BGR2RGB),
                                 caption=f"Cell",
                                 use_column_width=False, width=350)
                        cell_text = ocr_cell(cell_image, ocr_reader)
                        row_data.append(cell_text)
                    table_data.append(row_data)
                st.write("Extracted Table Data:")
                st.table(table_data)
        elif display_tables and not table_contours:
            st.write(f"No tables detected on page {i + 1}")
