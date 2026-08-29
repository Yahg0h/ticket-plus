# Base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies required by some Python packages (cryptography, Pillow, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install the cryptography package required for MySQL 8+ authentication
RUN pip install --no-cache-dir cryptography

# Copy all source files
COPY . .

# Expose the application port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
