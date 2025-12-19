FROM python:3.11-slim

RUN pip install --no-cache-dir --upgrade pip

WORKDIR /app

# 🔥 Cache buster — change value to force rebuild
ARG CACHEBUST=2

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8080
CMD ["python", "app.py"]
