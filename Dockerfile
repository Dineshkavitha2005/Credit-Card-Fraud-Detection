# ==============================================================================
# Credit Card Fraud Detection System - Production Dockerfile
# Multi-stage optimized, non-root security hardened container
# ==============================================================================

# Base image: Python 3.11 slim Debian Bookworm
FROM python:3.11-slim-bookworm

# Set metadata labels
LABEL maintainer="DevOps Team <devops@fraudshield.com>"
LABEL description="Production Docker image for Credit Card Fraud Detection System"
LABEL version="2.0.0"

# Set environment variables for Python runtime optimization
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    FLASK_ENV=production \
    PORT=5000 \
    PATH="/home/appuser/.local/bin:$PATH"

# Install minimal OS dependencies and healthcheck utility (curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    bash \
    libpq5 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged application user and group (least-privilege principle)
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -m -s /bin/bash appuser

# Set working directory
WORKDIR /app

# Create persistent storage directories and assign ownership to appuser
RUN mkdir -p /app/data /app/instance/reports && \
    chown -R appuser:appgroup /app

# Copy requirements file first to maximize Docker layer caching
COPY --chown=appuser:appgroup requirements.txt ./

# Install Python packages as non-root user
USER appuser
RUN pip install --no-cache-dir --user --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --user -r requirements.txt

# Switch back to root temporarily to copy application source and set execution permissions
USER root
COPY --chown=appuser:appgroup . .

# Ensure entrypoint script has executable permissions
RUN chmod +x /app/entrypoint.sh && \
    chown -R appuser:appgroup /app

# Switch to non-root user for runtime execution
USER appuser

# Expose standard application port
EXPOSE 5000

# Container healthcheck probe (verifies both HTTP service and DB connectivity)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Configure entrypoint and default command
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:app"]
