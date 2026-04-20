FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy pipeline code
COPY daily_run.py .
COPY auth_middleware.py .

# Run the daily pipeline
CMD ["python", "daily_run.py"]
