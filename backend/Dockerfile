FROM python:3.13-slim
WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/config.py .
COPY backend/tools.py .
COPY backend/server.py .
COPY backend/sandbox.py .

EXPOSE 8001

# Default workspace path
ENV AGENT_WORKSPACE=/app/workspace

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
