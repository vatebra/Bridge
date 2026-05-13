# Use the official Microsoft Playwright image as the base
# This image comes pre-loaded with Python, Chromium, and all system dependencies
FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file first to leverage Docker's caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code (app.py, etc.)
COPY . .

# Set environment variables
# Render typically uses port 10000 for Docker services
ENV PORT=10000
ENV PYTHONUNBUFFERED=1

# Expose the port for external access
EXPOSE 10000

# Start the application using Gunicorn
# Timeout is increased to 120s to allow the browser time to process the WAEC result
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "--timeout", "120", "app:app"]
