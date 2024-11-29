FROM python:3.13
LABEL authors="cosmdandy"

COPY . .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

WORKDIR src

ENTRYPOINT ["python", "main.py"]