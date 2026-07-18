FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN addgroup --system api && adduser --system --ingroup api api
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini main.py ./
RUN chown -R api:api /app
USER api
EXPOSE 8000
CMD ["python", "main.py"]
