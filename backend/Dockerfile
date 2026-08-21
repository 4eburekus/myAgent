FROM python:3.13-slim
WORKDIR /app

# Зависимости
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Приложение
COPY backend/config.py .
COPY backend/tools.py .
COPY backend/server.py .
COPY backend/sandbox.py .

EXPOSE 8001

# Работчая папка в контейнере
ENV AGENT_WORKSPACE=/app/workspace

# Запускаем FastAPI-приложение через ASGI-сервер uvicorn
# server:app = модуль server.py, объект app = FastAPI
# --host 0.0.0.0 = доступен извне контейнера
# --port 8001 = порт 8001
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
