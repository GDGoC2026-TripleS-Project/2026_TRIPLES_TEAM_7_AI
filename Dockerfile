FROM python:3.9-bullseye

WORKDIR /app

RUN apt-get update && apt-get install -y openjdk-11-jdk && apt-get clean
RUN apt-get update && apt-get install -y chromium unzip curl \
    && curl -sSL https://chromedriver.storage.googleapis.com/120.0.6099.224/chromedriver_linux64.zip -o /tmp/chromedriver.zip \
    &&unzip /tmp/chromedriver.zip -d /usr/bin \
    && rm /tmp/chromedriver.zip

ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV PATH=$JAVA_HOME/bin:$PATH

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
