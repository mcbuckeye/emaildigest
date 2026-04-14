# Backend Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -U pip
RUN pip install --no-cache-dir -e .

# Copy source code
COPY src/ ./src/
COPY celery_worker.py .
COPY src/templates/ ./src/templates/

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
