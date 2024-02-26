# Pull base image
FROM python:3.10

# Set work directory
WORKDIR /app

# Установка зависимостей для Selenium и Chrome
RUN apt update
RUN apt install -y \
    wget \
    xvfb \
    unzip \
    libxi6 \
    libgconf-2-4 \
    libnss3

# Установка Chrome
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN dpkg -i google-chrome-stable_current_amd64.deb; apt-get -fy install

# # Скачивание и распаковка Chrome
# RUN wget -q https://storage.googleapis.com/chrome-for-testing-public/122.0.6261.69/linux64/chrome-linux64.zip \
#     && unzip chrome-linux64.zip -d /opt/ \
#     && ln -s /opt/chrome-linux/chrome /usr/bin/google-chrome \
#     && rm chrome-linux64.zip

# # Установка ChromeDriver
# RUN wget https://storage.googleapis.com/chrome-for-testing-public/122.0.6261.69/linux64/chromedriver-linux64.zip
# RUN unzip chromedriver-linux64.zip -d /usr/bin/
# # RUN mv chromedriver /usr/bin/chromedriver
# # RUN chmod +x /usr/bin/chromedriver

RUN apt-get update && apt-get install -y chromium-driver
RUN chmod +x /usr/bin/chromedriver

# Copy project
COPY . /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install dependencies
RUN pip install -r requirements.txt
