FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
COPY requirements-ocr.txt ./requirements-ocr.txt
RUN pip install --no-cache-dir -r requirements.txt

# Para imagen Docker con OCR real, construir con:
# docker build --build-arg INSTALL_EASYOCR=true -t recetas-backend ./backend
ARG INSTALL_EASYOCR=false
RUN if [ "$INSTALL_EASYOCR" = "true" ]; then pip install --no-cache-dir -r requirements-ocr.txt; fi

COPY app ./app
RUN mkdir -p /app/uploads /app/data

EXPOSE 8000
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
