FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir pylint PyGithub PyYAML

COPY qa/ ./qa/
COPY default.pylintrc .

ENV PYTHONPATH=/app

ENTRYPOINT ["python", "-m", "qa.main"]
