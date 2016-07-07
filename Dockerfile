FROM python:3.5
ENV PYTHONUNBUFFERED 1

ADD requirements.txt /app/requirements.txt
RUN cd /app && pip install -r requirements.txt

RUN useradd -ms /bin/bash foosball

ADD . /app
WORKDIR /app
USER foosball

EXPOSE 8000
ENV PORT 8000

CMD uwsgi foosball/uwsgi.ini
