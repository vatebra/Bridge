FROM python:3.10-slim

# Prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Set the port to 10000 (Render's default)
EXPOSE 10000

# Run with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
