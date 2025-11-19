# Use the existing working Kokoro FastAPI image as base
FROM ghcr.io/remsky/kokoro-fastapi-gpu:latest

# Reset entrypoint to avoid conflicts with base image
ENTRYPOINT []

# Copy the serverless handler
COPY handler-wrapper.py /app/handler.py

# Switch to root to install runpod in the existing virtual environment
USER root
# Debug: List venv contents to verify path
RUN ls -la /app/.venv/bin || echo "Venv bin not found"
RUN /app/.venv/bin/pip install runpod>=1.0.0

# Switch back to appuser
USER appuser

# Set environment variables for the wrapper
ENV PYTHONPATH=/app:/app/api
ENV PATH="/app/.venv/bin:$PATH"

# Run the serverless handler directly
CMD ["python", "/app/handler.py"]
