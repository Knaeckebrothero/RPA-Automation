FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies including Tesseract and required libraries for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    tesseract-ocr \
    tesseract-ocr-deu \
    libtesseract-dev \
    poppler-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    # Install PyTorch with CUDA support
    pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu118

# Copy application files
COPY src/ ./src/
COPY examples/ ./examples/
COPY .env.example ./.env
COPY README.md ./
COPY table_detection.py ./

# Create necessary directories with appropriate permissions
RUN mkdir -p ./.filesystem/downloads \
    && mkdir -p ./.filesystem/logs \
    && chmod -R 777 ./.filesystem

# Expose Streamlit port
EXPOSE 8501

# Default locations for logs and filesystem
# These can be overridden by environment variables at runtime
ENV LOG_PATH=./.filesystem/logs/ \
    FILESYSTEM_PATH=./.filesystem/

# All other configuration will be provided through environment variables at runtime:
# DEV_MODE, LOG_LEVEL_CONSOLE, LOG_LEVEL_FILE, OCR_USE_GPU
# IMAP_HOST, IMAP_PORT, IMAP_USER, IMAP_PASSWORD, INBOX

# Initialize the database on startup and then run the app
CMD ["sh", "-c", "python examples/db_init.py && streamlit run src/main.py --server.address=0.0.0.0"]
