"""
This module holds methods to extract text from images.
"""
import logging as log
import os
import cv2
import numpy as np
from PIL import Image
from easyocr import Reader


def ocr_cell(cell_image, reader: Reader = None) -> str:
    """
    Perform OCR on a cell image using EasyOCR.

    :param cell_image: The image of the cell to perform OCR on.
    :param reader: The EasyOCR reader instance. If None, a new reader will be created.
    :return: The extracted text from the cell image.
    """
    # Create a new reader if one wasn't provided
    if reader is None:
        reader = create_ocr_reader()

    # Perform OCR
    result = reader.readtext(cv2.cvtColor(cell_image, cv2.COLOR_BGR2RGB))

    # Extract the recognized text
    text = ' '.join([res[1] for res in result])
    log.debug(f'Extracted text from cell: {text}')

    # If no text was found, try to detect if it's a single digit cell
    if not text.strip():
        log.debug('No text found, checking if cell contains a single digit')
        text = _handle_empty_cell_result_easyocr(cell_image, reader)

    return text.strip()


def create_ocr_reader(language: str = 'en', use_gpu: bool = False) -> Reader:
    """
    Create an EasyOCR reader instance with GPU support if available and enabled.

    :param language: The language for OCR. Default is 'en' (English).
    :param use_gpu: Boolean flag to indicate if GPU should be used. Default is False.
    :return: An EasyOCR reader instance
    """
    if not use_gpu:
        # Check if GPU should be used (default is False)
        use_gpu = os.getenv('OCR_USE_GPU', 'false').lower() in ('true', '1', 'yes')

    if use_gpu:
        try:
            import torch
            gpu_available = torch.cuda.is_available()
            if gpu_available:
                log.info('GPU is available and OCR_USE_GPU is set. Using GPU for OCR.')
                return Reader([language], gpu=True)
            else:
                log.warning('OCR_USE_GPU is set but no GPU is available. Falling back to CPU.')
                return Reader([language], gpu=False)
        except ImportError:
            log.warning('OCR_USE_GPU is set but PyTorch is not properly installed. Falling back to CPU.')
            return Reader([language], gpu=False)
    else:
        log.debug('Using CPU for OCR processing (OCR_USE_GPU not set).')
        return Reader([language], gpu=False)


def ocr_cell_tesseract(cell_image) -> str:
    """
    Perform OCR on a cell image using Tesseract.
    This is kept for testing purposes but not used in production.

    :param cell_image: The image of the cell to perform OCR on.
    :return: The extracted text from the cell image.
    """
    # Convert to PIL Image for Tesseract
    pil_image = Image.fromarray(cv2.cvtColor(cell_image, cv2.COLOR_BGR2RGB))
    log.debug('Converted cell image to PIL Image')

    # Perform OCR
    import pytesseract  # Import here to avoid dependency in production
    text = pytesseract.image_to_string(pil_image)  # , config='--psm 6'
    log.debug(f'Extracted text from cell: {text}')

    return text.strip()


def _handle_empty_cell_result_easyocr(cell_image, reader: Reader) -> str:
    """
    Handle cases where EasyOCR doesn't detect any text in a cell.
    This function tries specialized approaches for single digits,
    particularly focusing on detecting "0" values.

    :param cell_image: The cell image that returned no OCR results
    :param reader: The EasyOCR reader instance
    :return: The detected text or "0" if a digit-like pattern is found
    """
    # Convert to grayscale if it's not already
    if len(cell_image.shape) == 3:
        gray = cv2.cvtColor(cell_image, cv2.COLOR_BGR2GRAY)
    else:
        gray = cell_image

    # Apply thresholding to isolate potential text
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

    # Find contours in the thresholded image
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Check if there are any contours of reasonable size
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        # Filter out very small contours (noise)
        if w > 3 and h > 3:
            # Try EasyOCR with enhanced preprocessing
            roi = thresh[y:y+h, x:x+w]

            # Ensure the ROI is large enough
            if w > 5 and h > 5:
                # Resize to make digit more prominent
                resized_roi = cv2.resize(roi, (w*3, h*3), interpolation=cv2.INTER_CUBIC)

                # Try EasyOCR again with the enhanced image
                result = reader.readtext(resized_roi,
                                         allowlist='0123456789',
                                         detail=0)

                if result:
                    log.debug(f'Detected digit: {result[0]} using enhanced approach')
                    return result[0]

                # If still nothing is found but we have a contour that looks like a digit
                # (especially a 0), return "0" as a fallback
                area_ratio = cv2.contourArea(contour) / (w * h)
                # A "0" often has an area ratio around 0.4-0.6 (the hole in the middle)
                if 0.3 <= area_ratio <= 0.7:
                    # Check if the contour is roughly circular/oval (like a "0")
                    perimeter = cv2.arcLength(contour, True)
                    circularity = 4 * np.pi * cv2.contourArea(contour) / (perimeter * perimeter) if perimeter > 0 else 0

                    if circularity > 0.4:  # A circle has circularity of 1.0
                        log.debug('Found a contour that looks like a "0", using fallback value')
                        return "0"

    # If we've gotten here, check the entire cell for a single small digit
    # Look for any non-white pixel
    non_zero_pixels = np.count_nonzero(thresh)
    if 5 < non_zero_pixels < 100:  # Some reasonable threshold for a single digit
        log.debug('Found some non-white pixels in the cell, assuming it contains a "0"')
        return "0"

    # If we've gotten here, there's probably no digit in the cell
    log.debug('No digits detected in the cell, returning empty string')
    return ""
