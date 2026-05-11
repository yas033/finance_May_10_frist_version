FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8765

WORKDIR /app
COPY server.py pyproject.toml README.md ./
COPY quanttool ./quanttool
COPY web ./web
COPY web/app.js web/styles.css ./
COPY examples ./examples
COPY tests ./tests

EXPOSE 8765
CMD ["python", "server.py"]
