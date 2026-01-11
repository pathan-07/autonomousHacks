# backend/Dockerfile

# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Hardcoded API URL for Hackathon Deployment
ENV NEXT_PUBLIC_API_URL=https://scamshield-backend-457750343726.us-central1.run.app

# Copy requirements and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 8080
EXPOSE 8080

# Command to run the application using Uvicorn.
# Cloud Run (and some other GCP runtimes) provide the listening port via $PORT.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]