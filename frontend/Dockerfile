FROM python:3.13-slim
WORKDIR /app

COPY frontend/requirements.txt .
# --no-cache-dir убирает кэш pip для экономии места
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения в контейнер в /app
COPY frontend/app.py .
COPY backend/config.py .
COPY backend/tools.py .

EXPOSE 8000

# Устанавливаем переменную окружения — URL WebSocket для подключения к бэкенду
ENV BACKEND_WS_URL=ws://backend:8001/ws

# запускаем приложение через chainlit run app.py на порту 8000, доступном извне (0.0.0.0)
CMD ["chainlit", "run", "app.py", "--port", "8000", "--host", "0.0.0.0"]
