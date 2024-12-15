FROM python:3.11-slim

# Avoid package configuration prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install essential packages
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    perl-base \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright dependencies
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libatspi2.0-0 \
    libwayland-client0 \
    # Additional dependencies
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libfontconfig1 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    fonts-liberation \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser in a non-interactive way
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install chromium --with-deps
RUN playwright install-deps

# Copy application code
COPY app/ app/
COPY .env .env

# Create directories for downloads and screenshots
RUN mkdir -p app/tmp/browserdownload
RUN mkdir -p app/tmp/browserscreenshots

# Set display for Playwright/Chromium
ENV DISPLAY=:99

# Set Timezone for container
ENV TZ=Asia/Bangkok

# Run with xvfb-run for headless browser support
CMD xvfb-run --server-args="-screen 0 1280x1024x24" gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 "app.app:app"