# Pull base image
FROM python:3.10

# Set work directory
WORKDIR /app

# Copy project
COPY . /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install dependencies
RUN pip install -r requirements.txt
