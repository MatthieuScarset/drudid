FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip install -U pip \
    && pip install -r requirements.txt

COPY app/ ./app/
COPY .env ./app/.env
COPY models/ /app/models/

CMD ["sh", "-c", "streamlit run app/run.py --server.port=${PORT} --server.address=0.0.0.0"]
