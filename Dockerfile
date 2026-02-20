FROM python:3.9-slim

WORKDIR /app

# 필수 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 전체 소스 복사 (model_A, model_B 폴더 포함)
COPY . .

# 루트의 main.py 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]