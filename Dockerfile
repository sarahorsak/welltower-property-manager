# Dockerfile

# Use the official Python base image
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements file first to leverage Docker caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Set environment variable for Flask to know where the app factory is
ENV FLASK_APP=src:create_app

# Expose the port Flask runs on
EXPOSE 5001

# Command to run the application:
# 1. Run pytest to execute all tests
# 2. Start the Flask application in development mode
# Note: For production, we would use a WSGI server like Gunicorn or uWSGI.
CMD /bin/bash -c "pytest && flask run --host=0.0.0.0"