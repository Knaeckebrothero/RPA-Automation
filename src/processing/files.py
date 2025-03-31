"""
This module contains functions for processing files.
"""
import io
import numpy as np
import logging
import fitz  # This is PyMuPDF
from PIL import Image


# Set up logging
log  = logging.getLogger(__name__)

def get_images_from_pdf(pdf_bytes: bytes) -> list[np.array]:
    pdf_doc = fitz.open("pdf", pdf_bytes)
    extracted_images = []

    for page_num in range(pdf_doc.page_count):
        try:
            page = pdf_doc[page_num]

            for img in page.get_images(full=True):
                xref = img[0]
                base_image = pdf_doc.extract_image(xref)
                image_bytes = base_image["image"]
                pil_image = Image.open(io.BytesIO(image_bytes))
                extracted_images.append(pil_image)  # stores the image in bytes
        except Exception as e:
            log.error(f"Error extracting image from PDF: {e}")
    return extracted_images


def create_certificate_file():
    """
    This function assembles a certificate proving that the company has been checked successfully.
    """
    pass # TODO: Implement this function
