FROM python:3.11.9

WORKDIR /app

COPY ./src/requirements.txt ./src/

RUN pip install -r src/requirements.txt

COPY . .

CMD ["python3", "src/main.py"]
