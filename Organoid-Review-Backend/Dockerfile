FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y pkg-config python3-dev default-libmysqlclient-dev build-essential

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "main.py"]