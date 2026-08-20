FROM python:3.13-slim
WORKDIR /app
COPY chatlist/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY chatlist/app.py .
EXPOSE 8002
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002"]
