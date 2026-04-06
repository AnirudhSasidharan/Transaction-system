# ── Dockerfile ────────────────────────────────────────────────────────────────
# WHAT IS THIS?
#   A script that builds a Docker image — a complete snapshot of your app
#   and everything it needs to run (Python, libraries, your code).
#
# HOW IT WORKS — each line is a "layer":
#   Docker caches each layer. If a layer hasn't changed, it reuses
#   the cached version instead of rebuilding. This makes rebuilds fast.
#
# WHY COPY requirements.txt BEFORE copying code?
#   requirements.txt changes rarely. Your code changes often.
#   By copying requirements first and running pip install, that layer
#   gets cached. Next time you change only your code, Docker skips
#   the pip install layer entirely — much faster rebuilds.
# ─────────────────────────────────────────────────────────────────────────────

# Start from official Python 3.12 slim image
# slim = smaller size, no unnecessary system packages
FROM python:3.12-slim

# Set working directory inside the container
# All subsequent commands run from /app
WORKDIR /app

# Install system dependencies needed to compile Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (cached layer — only rebuilds if requirements change)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Run migrations then start the server
# alembic upgrade head → creates all tables in the DB
# uvicorn → the ASGI server that runs FastAPI
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
