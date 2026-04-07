FROM python:3.11-slim

WORKDIR /app

# Python deps
RUN pip install --no-cache-dir pylint PyGithub PyYAML

# Node.js 20 + ESLint
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# .NET SDK 8 (dotnet-format is built-in since .NET 6)
RUN apt-get update && \
    apt-get install -y wget apt-transport-https && \
    wget https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb -O packages-microsoft-prod.deb && \
    dpkg -i packages-microsoft-prod.deb && \
    rm packages-microsoft-prod.deb && \
    apt-get update && \
    apt-get install -y dotnet-sdk-8.0 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY qa/ ./qa/
COPY default.pylintrc .
COPY default.eslintrc.json .

ENV PYTHONPATH=/app

ENTRYPOINT ["python", "-m", "qa.main"]
