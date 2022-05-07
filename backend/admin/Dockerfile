FROM python:3.8.11-alpine3.13

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ENV ADMIN_STATIC_ROOT /data/static

WORKDIR /src

RUN apk upgrade --update-cache --available

RUN apk update

# Install bash and git
RUN apk add bash git

RUN rm /bin/sh && ln -s /bin/bash /bin/sh

# Update timeout command to be compatible with wait-for-it.sh
RUN apk --update add --no-cache coreutils

# Install required libs
RUN apk add gcc g++ libxslt-dev libxml2

# Install python and Pillow required libs
RUN apk add python3-dev musl-dev jpeg-dev

# Install PostgreSQL libraries
RUN apk add postgresql-dev && apk add postgresql-client --repository=http://dl-cdn.alpinelinux.org/alpine/v3.10/main

# Delete cache files used by apk
RUN rm -rf /var/cache/apk/*

# Delete cache files used by apk
RUN rm -rf /var/cache/apk/*

# Update pip
RUN python3 -m pip install --upgrade pip

# To speed up the build in test environments, e.g. on a continuous integration server,
# disable the C compiler optimisations by setting the CFLAGS environment variable.
# https://lxml.de/installation.html
RUN CFLAGS="-O0"

# Install nginx
RUN apk add nginx
COPY docker/nginx.conf /etc/nginx/nginx.conf
RUN mkdir /run/nginx

# Install Python requirements
COPY requirements.txt /src/requirements.txt
RUN python3 -m pip install --no-input -r /src/requirements.txt

COPY docker/wait-for-it.sh /src/docker/wait-for-it.sh
COPY docker/entrypoint.sh /src/docker/entrypoint.sh

COPY . /src

EXPOSE 8080

RUN addgroup -g 1000 app \
    && adduser -S -D -H -u 1000 -h /var/cache/nginx -s /sbin/nologin -G app -g app app
RUN mkdir -p /data
RUN chown -R app /data
RUN chown -R app /var/lib/nginx
RUN chown -R app /var/run/nginx

USER app

CMD ["/src/docker/entrypoint.sh"]
