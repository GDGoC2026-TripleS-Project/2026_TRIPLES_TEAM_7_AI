FROM python:3.9-bullseye

WORKDIR /app

RUN apt-get update && apt-get install -y openjdk-11-jdk && apt-get clean
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver

ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV PATH=$JAVA_HOME/bin:$PATH

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
