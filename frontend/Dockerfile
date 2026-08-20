FROM python:3.13-slim
WORKDIR /app

# Install dependencies
COPY frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy frontend code
COPY frontend/app.py .
COPY backend/config.py .
COPY backend/tools.py .

EXPOSE 8000

ENV BACKEND_WS_URL=ws://backend:8001/ws

CMD ["chainlit", "run", "app.py", "--port", "8000", "--host", "0.0.0.0"]
