FROM python:3.9-bullseye

WORKDIR /app

RUN apt-get update && apt-get install -y openjdk-11-jdk chromium && apt-get clean

ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV PATH=$JAVA_HOME/bin:$PATH

COPY requirements.txt .
RUN pip install -r requirements.txt \
    && pip install --upgrade selenium

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
