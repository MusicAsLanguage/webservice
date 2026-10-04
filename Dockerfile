FROM mcr.microsoft.com/mirror/docker/library/python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg openssh-server dialog \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /app
WORKDIR /app
COPY requirements.txt requirements-speech.txt /app/
RUN pip install -r requirements-speech.txt --no-cache-dir
COPY . /app/
ENV APP_ENV=prod

# ssh
ENV SSH_PASSWD="root:Docker!"
RUN echo "$SSH_PASSWD" | chpasswd

COPY sshd_config /etc/ssh/
COPY init.sh /usr/local/bin/

RUN chmod u+x /usr/local/bin/init.sh
EXPOSE 8000 2222
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=8)"

ENTRYPOINT ["init.sh"]