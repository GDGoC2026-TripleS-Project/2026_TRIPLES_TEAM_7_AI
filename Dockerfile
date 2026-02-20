FROM python:3.9-slim

WORKDIR /app

# Java 설치
RUN apt-get update && apt-get install -y openjdk-11-jdk && apt-get clean

# 환경변수 설정
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV PATH=$JAVA_HOME/bin:$PATH

# 필수 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 전체 소스 복사 (model_A, model_B 폴더 포함)
COPY . .

# 루트의 main.py 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]