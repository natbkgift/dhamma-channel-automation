# Base image
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git && \
    rm -rf /var/lib/apt/lists/*

# Copy project
COPY . /app

# Install web deps + project (editable install for existing package)
RUN pip install --no-cache-dir -r requirements.web.txt && \
    pip install --no-cache-dir -e .

EXPOSE 8000
ENV APP_NAME="dhamma-automation"
ENV ADMIN_USERNAME="admin"
ENV ADMIN_PASSWORD="admin123"
ENV OUTPUT_DIR="./output"

RUN mkdir -p ${OUTPUT_DIR}

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
