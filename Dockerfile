FROM python:3.9-slim

WORKDIR /app

# Create the virtual environment at build time so the layer is cacheable.
ENV VIRTUAL_ENV=/app/.venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install Python dependencies (cached layer — only rebuilt when requirements.txt changes).
COPY requirements.txt .
RUN pip install --upgrade pip --quiet && \
    pip install -r requirements.txt --quiet

# Copy the rest of the application.
COPY . .

# Make management scripts executable.
RUN chmod +x bootstrap-mu2e-rundb-viewer start-mu2e-rundb-viewer stop-mu2e-rundb-viewer

# Default environment — override at runtime via -e or docker-compose env_file.
ENV DJANGO_ENV=production
ENV DJANGO_SETTINGS_MODULE=runlogdb.settings
ENV RUNLOGDB_HOST=0.0.0.0
ENV RUNLOGDB_PORT=8000

EXPOSE 8000

# start-mu2e-rundb-viewer detects /.dockerenv and runs gunicorn in the foreground.
CMD ["./start-mu2e-rundb-viewer"]
