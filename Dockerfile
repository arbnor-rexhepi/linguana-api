FROM python:3.8.8-buster

ENV DockerHOME=/home/app/

WORKDIR $DockerHOME

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ADD ./requirements.txt $DockerHOME/requirements.txt

ADD . $DockerHOME

RUN python -m pip install --upgrade pip

RUN pip3 install -r requirements.txt

RUN flake8 .

RUN python manage.py test

RUN chmod +x docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["sh", "docker-entrypoint.sh"]
