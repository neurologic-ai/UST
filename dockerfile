
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file to the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the FastAPI app code to the container
COPY . .

# Expose the port that the application listens on.
EXPOSE 8000

# Run the application.
CMD [
  "gunicorn", "main:backend_app",
  "-k", "uvicorn.workers.UvicornWorker",
  "--workers", "4",
  "--worker-connections", "1000",
  "--timeout", "90",
  "--keep-alive", "5",
  "--bind", "0.0.0.0:8000"
]
