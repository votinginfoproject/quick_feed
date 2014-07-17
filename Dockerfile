FROM quay.io/democracyworks/base:latest
MAINTAINER Democracy Works, Inc. <dev@democracy.works>

RUN apt-get install -y postgresql libpq-dev python python-setuptools python-dev \
                       build-essential python-pip libxslt1-dev

USER postgres
RUN /etc/init.d/postgresql start &&\
    psql --command "CREATE USER vip WITH SUPERUSER PASSWORD 'vip';" &&\
    createdb -O vip vip
VOLUME ["/etc/postgresql", "/var/log/postgresql", "/var/lib/postgresql"]

USER root

RUN mkdir /quick_feed
WORKDIR /quick_feed

ADD ./requirements.txt /quick_feed/
RUN pip install -r requirements.txt

VOLUME ["/data", "/reports", "/feeds"]
ADD ./ /quick_feed/

ENTRYPOINT ["/quick_feed/run_quick_feed", "--data-type", "db_flat", "--report-dir", "/reports", "--feed-dir", "/feeds", "--dbname", "vip", "--dbuser", "vip", "--dbpass", "vip", "/data"]
