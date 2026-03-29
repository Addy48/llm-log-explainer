FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY index.html .

EXPOSE 3000

CMD ["python", "-m", "http.server", "3000"]
