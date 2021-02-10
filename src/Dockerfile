FROM python:3.8-slim 

RUN pip install --upgrade pip && \
    pip install --no-cache-dir python-telegram-bot sqlalchemy emoji --upgrade

WORKDIR /src
COPY . . 

ENTRYPOINT ["python", "/src/mainbot.py"]