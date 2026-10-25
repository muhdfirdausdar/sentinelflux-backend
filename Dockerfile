# Multi-stage build for efficient Docker image
FROM python:3.13.3-slim-bookworm AS builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    redis-tools \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Set timezone to UTC+8 (Kuala Lumpur)
RUN ln -fs /usr/share/zoneinfo/Asia/Kuala_Lumpur /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata

# Set working directory
WORKDIR /app

# Copy requirements file first for better caching
COPY requirements.txt ./

# Install Python packages globally with pip cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy source code
COPY . .

# Make start script executable
RUN chmod +x /app/start_script.sh

# --- Final image ---
FROM python:3.13.3-slim-bookworm

# Copy tzdata and system dependencies from builder
RUN apt-get update && apt-get install -y \
    libpq-dev \
    redis-tools \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Set timezone to UTC+8 (Kuala_Lumpur)
RUN ln -fs /usr/share/zoneinfo/Asia/Kuala_Lumpur /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata

# Create non-root user and group with specific UID/GID to match docker-compose.yml
RUN groupadd -g 1000 appuser && useradd -m -u 1000 -g 1000 appuser

# Create secrets directory and set permissions for Docker secrets
RUN mkdir -p /run/secrets && chown root:appuser /run/secrets && chmod 750 /run/secrets

# Set working directory
WORKDIR /app

# Copy global Python packages and binaries from builder
COPY --from=builder /usr/local /usr/local
# Copy only necessary files from builder
COPY --from=builder /app /app

# Set permissions
RUN chown -R appuser:appuser /app

# Ensure ~/.local/bin is in PATH for appuser (for pip --user installs)
ENV PATH="/home/appuser/.local/bin:$PATH"

# Switch to non-root user
USER appuser

# Expose FastAPI port
EXPOSE 5252

CMD ["/app/start_script.sh"]
