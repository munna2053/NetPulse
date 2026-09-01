FROM python:3.11-slim

WORKDIR /app

COPY . /app

# Install dependencies if requirements.txt exists
RUN pip install --no-cache-dir --upgrade pip \
    && if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

EXPOSE 8765

# Run NetPulse with HOST overridden to 0.0.0.0 so it's reachable outside the container
CMD ["python", "-c", "import internet_tester as app; app.HOST='0.0.0.0'; app.main()"]
