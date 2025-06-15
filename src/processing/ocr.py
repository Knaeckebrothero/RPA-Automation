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
    Performs OCR (Optical Character Recognition) on a provided cell image to extract
    text content. If a pre-initialized OCR reader is not provided, a new one is
    created internally. In cases where no text is detected in the cell, it attempts
    an additional process for identifying content such as single digits.

    :param cell_image: The image of the cell to process for text extraction.
    :type cell_image: numpy.ndarray
    :param reader: An optional EasyOCR Reader instance for performing OCR.
                   If not provided, a default reader will be created.
    :type reader: Reader, optional
    :return: The text extracted from the cell image after performing OCR.
    :rtype: str
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
    Creates an OCR Reader object with specified language and hardware preference (CPU or GPU). This function
    allows using a GPU for OCR processing if available and explicitly requested or defaults to CPU otherwise.
    The function will check the environment variable 'OCR_USE_GPU' and use its value if the `use_gpu` parameter
    is not explicitly provided.

    :param language: Language to be used by the OCR Reader. Defaults to 'en' (English).
    :type language: str
    :param use_gpu: Flag indicating whether to enable GPU for OCR processing. Defaults to False.
                    If not explicitly provided, this flag is determined by the 'OCR_USE_GPU' environment
                    variable ('true', '1', 'yes' for GPU; otherwise CPU).
    :type use_gpu: bool
    :return: An OCR Reader instance configured to process text in the specified language using either CPU or GPU.
    :rtype: Reader
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
    Extracts text from a given cell image using Tesseract OCR.

    This function takes an image of a cell as input, processes it to be compatible
    with Tesseract OCR, and extracts textual content from it. The input is expected
    to be a cell image in OpenCV's format, which is converted to a PIL Image before
    passing it to Tesseract OCR. The extracted text is stripped of leading and
    trailing whitespace before being returned.

    :param cell_image: The input image of a cell from which text needs to be extracted.
    :type cell_image: numpy.ndarray
    :return: The textual content extracted from the cell image.
    :rtype: str
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
    Attempts to interpret possible numeric content in an image of a single cell using enhanced preprocessing
    and EasyOCR. The function first applies grayscale conversion and thresholding before analyzing contours
    for plausible text regions. If contours suggest the presence of numeric elements, enhanced preprocessing
    such as resizing and examining ratios of dimensions and area are used to identify numeric shapes.
    Fallback mechanisms like detecting specific contour characteristics, such as circularity, are implemented
    to identify the digit "0" in ambiguous cases. If no numeric content is found, an empty string is returned.

    :param cell_image: Image of the cell to be analyzed. Could be in grayscale or color.
    :type cell_image: numpy.ndarray
    :param reader: Pre-initialized EasyOCR reader instance for OCR detection of numbers.
    :type reader: Reader
    :return: Numeric content detected in the cell, or an empty string if none is found.
    :rtype: str
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
