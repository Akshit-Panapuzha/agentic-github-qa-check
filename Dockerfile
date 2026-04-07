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

# .NET SDK 8 via official install script (avoids apt repo SHA1 signing key issue)
RUN curl -fsSL https://dot.net/v1/dotnet-install.sh -o dotnet-install.sh && \
    chmod +x dotnet-install.sh && \
    ./dotnet-install.sh --channel 8.0 --install-dir /usr/local/dotnet && \
    rm dotnet-install.sh && \
    ln -s /usr/local/dotnet/dotnet /usr/local/bin/dotnet

COPY qa/ ./qa/
COPY default.pylintrc .
COPY default.eslintrc.json .

ENV PYTHONPATH=/app

ENTRYPOINT ["python", "-m", "qa.main"]
