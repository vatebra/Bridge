FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app.py .

# Render dynamically assigns a port, but we use 5000 as a default
EXPOSE 5000

# Use Gunicorn for production stability
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
