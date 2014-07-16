FROM quay.io/democracyworks/base:latest
MAINTAINER Democracy Works, Inc. <dev@democracy.works>

RUN apt-get install -y postgresql libpq-dev python python-setuptools python-dev \
                       build-essential python-pip libxslt1-dev

RUN mkdir /quick_feed
WORKDIR /quick_feed

ADD ./requirements.txt /quick_feed/
RUN pip install -r requirements.txt

ADD ./ /quick_feed/

ENTRYPOINT ["python", "quick_feed.py"]
