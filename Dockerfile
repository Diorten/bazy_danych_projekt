# syntax=docker/dockerfile:1
FROM python:3.9
WORKDIR /code
# RUN apk add --no-cache gcc musl-dev linux-headers
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY ./app /code/app
COPY ./certs /code/app/certs
RUN echo "nameserver 8.8.8.8" > /etc/resolv.conf
CMD ["uvicorn", "app.main:app", "--ssl-keyfile=app/key.pem", "--ssl-certfile=app/cert.pem", "--host", "0.0.0.0", "--port", "443"]
