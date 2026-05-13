# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables to prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies needed for Playwright and Chromium
# These are essential to avoid 'browser type not found' or execution errors
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
# Note: Ensure playwright-stealth is REMOVED from your requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser and its specific system-level dependencies
# This replaces the 'manual' build command in the Render dashboard
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy the rest of your application code
COPY . .

# Expose the port Flask/Gunicorn will run on
EXPOSE 10000

# Start the application using Gunicorn for better production performance
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
