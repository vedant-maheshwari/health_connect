FROM python:3.11-slim

WORKDIR /app

# Copy shared modules
COPY shared/ /app/shared/

# Copy gateway files
COPY api-gateway/ /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8000

# Run the gateway
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
