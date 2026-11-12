FROM python:3.10-slim

WORKDIR /app
COPY . /app

RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip install -r requirements.txt

EXPOSE 9000
CMD ["streamlit", "run", "app.py", \
     "--server.port=9000", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
