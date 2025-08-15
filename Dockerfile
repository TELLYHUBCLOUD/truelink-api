FROM python:3.11-slim

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# Install system dependencies (Playwright, Chromium, fonts, build tools)
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    build-essential \
    python3-dev \
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
    libasound2 \
    libxshmfence1 \
    libgl1 \
    libglib2.0-0 \
    fonts-noto \
    fonts-noto-cjk \
    fonts-unifont \
    fonts-dejavu-core \
    wget \
    unzip \
    git \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY requirements.txt .

# Ensure pip is up-to-date
RUN python3 -m ensurepip --upgrade && \
    pip install --no-cache-dir --upgrade pip

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade truelink && \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright + Chromium
RUN npx playwright install --with-deps chromium

# Copy project files
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app

USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

EXPOSE 5000

# Run app
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
