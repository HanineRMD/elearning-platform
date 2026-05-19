FROM python:3.11-slim

WORKDIR /app

# Solution anti-timeout avec miroir Alibaba
COPY requirements.txt .
RUN pip install --no-cache-dir \
    -i https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com \
    --default-timeout=100 \
    -r requirements.txt

COPY . .

EXPOSE 8003

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8003", "--reload"]