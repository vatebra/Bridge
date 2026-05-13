# 1. Use the Playwright image that matches our requirements
FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

# 2. Set the working directory
WORKDIR /app

# 3. Copy requirements first for better caching
COPY requirements.txt .

# 4. Install Python dependencies
# Using --no-cache-dir keeps the image size smaller
RUN pip install --no-cache-dir -r requirements.txt

# 5. CRITICAL FIX: Install the Chromium browser binaries
# This solves the "Executable doesn't exist" error you saw
RUN playwright install chromium

# 6. Copy the rest of your app code
COPY . .

# 7. Environment Variables
ENV PORT=10000
ENV PYTHONUNBUFFERED=1

# 8. Expose the port
EXPOSE 10000

# 9. Start the app
# Increased timeout to 120s to handle the slow WAEC portal response
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "--timeout", "120", "app:app"]
