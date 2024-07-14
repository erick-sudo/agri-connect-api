FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --upgrade pip
COPY requirements.txt /app/requirements.txt
# Allows docker to cache installed dependencies between builds
RUN pip install --no-cache-dir -r requirements.txt

# Mounts the application code to the image
COPY . /app

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Set the entry point
ENTRYPOINT ["./entrypoint.sh"]

EXPOSE 8000

CMD ["gunicorn", "--config", "gunicorn_config.py", "app.wsgi:application"]