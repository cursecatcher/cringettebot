FROM python:3.8-slim 

RUN pip install --upgrade pip && \
    pip install --no-cache-dir --upgrade python-telegram-bot sqlalchemy emoji 

WORKDIR /src
COPY . . 

ENTRYPOINT ["python", "/src/cringe.py"]