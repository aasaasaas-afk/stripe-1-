FROM python:3.9-slim

WORKDIR /app

# Upgrade pip to avoid warnings
RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Use a default PORT if not set, but allow Render to override it
ENV PORT=8000

# Use exec form to ensure proper signal handling
CMD exec gunicorn --bind 0.0.0.0:$PORT app:app
