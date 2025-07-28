FROM python:3.11-slim

WORKDIR /app

# Install system dependencies and uv
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH
ENV PATH="/root/.cargo/bin:$PATH"

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Install dependencies with uv
RUN uv sync --frozen --no-dev

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 8000

# Run the application using uv
CMD ["uv", "run", "python", "-m", "src.main"]