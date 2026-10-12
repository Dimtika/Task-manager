FROM python:3.12.15-alpine

EXPOSE 8000

WORKDIR /app

COPY requirements.txt .

RUN apk add --no-cache build-base pkgconf mariadb-dev \
&& pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["fastapi", "dev", "--host", "0.0.0.0"]