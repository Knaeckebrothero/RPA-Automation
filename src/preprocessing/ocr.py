"""
This module holds methods to extract text from images.
"""
import logging as log
import cv2
import pytesseract
import easyocr
from PIL import Image


def ocr_cell(cell_image):
    # Initialize EasyOCR reader
    reader = easyocr.Reader(['de'])
    log.debug('Initialized EasyOCR reader')

    # Perform OCR
    result = reader.readtext(cv2.cvtColor(cell_image, cv2.COLOR_BGR2RGB))
    log.debug(f'Extracted text from cell: {result}')

    # Extract the recognized text
    text = ' '.join([res[1] for res in result])

    return text.strip()


def ocr_cell_tesseract(cell_image):
    # Convert to PIL Image for Tesseract
    pil_image = Image.fromarray(cv2.cvtColor(cell_image, cv2.COLOR_BGR2RGB))
    log.debug('Converted cell image to PIL Image')

    # Perform OCR
    text = pytesseract.image_to_string(pil_image)  # , config='--psm 6'
    log.debug(f'Extracted text from cell: {text}')

    return text.strip()
