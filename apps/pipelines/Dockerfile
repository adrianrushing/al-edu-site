FROM python:3.13-slim

WORKDIR /app

# Install system deps for psycopg2
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy pipeline code
COPY . .

# Default: run the sample clean script (CSV ingest → PostgreSQL)
CMD ["python", "silver/sample_clean.py"]
