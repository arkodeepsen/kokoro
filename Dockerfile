# Use the existing working Kokoro FastAPI image as base
FROM ghcr.io/remsky/kokoro-fastapi-gpu:latest

# Reset entrypoint to avoid conflicts with base image
ENTRYPOINT []

# Copy the serverless handler
COPY handler-wrapper.py /app/handler.py

# Switch to root to install runpod in the existing virtual environment
# Debug: Explore environment to find where things are
RUN echo "--- Environment Check ---" && \
    ls -la /app && \
    which python && \
    python --version && \
    echo "-------------------------"

# Install runpod using the detected python
RUN python -m pip install runpod>=1.0.0

# Switch back to appuser
USER appuser

# Set environment variables for the wrapper
ENV PYTHONPATH=/app:/app/api
# Ensure the python we found is in path (it should be by default, but we keep the venv one just in case it exists but was missed, though likely we should just trust PATH)
# ENV PATH="/app/.venv/bin:$PATH" 
# Commenting out the forced venv path to rely on system PATH which seems to be what works for 'python'

# Run the serverless handler directly
CMD ["python", "/app/handler.py"]
