# syntax=docker/dockerfile:1
#
# Dream AI container image.
# Runtime configuration is supplied through environment variables
# (see `.env.example`); no secret is baked into the image. Without an
# `DREAMAI_API_KEY` the assistant starts in offline demo mode.

FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install runtime dependencies first so this layer is cached across source edits.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project metadata and source, then install the package.
# README.md and LICENSE are required by the packaging metadata in pyproject.toml.
COPY pyproject.toml README.md LICENSE ./
COPY dream_ai ./dream_ai
RUN pip install --no-cache-dir .

# Run as a non-root user for a safer default container.
RUN useradd --create-home --uid 10001 dream \
    && chown -R dream:dream /app
USER dream

# Interactive REPL: `docker run -it --rm ghcr.io/li-guijiang/dream-ai:latest`
ENTRYPOINT ["python", "-m", "dream_ai"]
