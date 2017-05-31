FROM ubuntu:latest

MAINTAINER Jacopo Daeli <jacopo.daeli@gmail.com>

ENV PILBOX_DIR=/pilbox

EXPOSE 8888

RUN sudo apt-get update -qq && \
  apt-get install python -yqq && \
  apt-get install python-dev -yqq && \
  apt-get install python-setuptools -yqq && \
  apt-get install python-pip -yqq && \
  apt-get install python-numpy -yqq && \
  apt-get install python-opencv -yqq && \
  apt-get install python-pycurl -yqq && \
  apt-get install libjpeg-dev -yqq && \
  apt-get install libfreetype6-dev -yqq && \
  apt-get install zlib1g-dev -yqq && \
  apt-get install libwebp-dev -yqq && \
  apt-get install liblcms2-dev -yqq && \
  apt-get install python -yqq && \
  apt-get install python -yqq && \
  pip install Pillow==2.8.1 && \
  pip install tornado==4.0.2 && \
  pip install coverage==3.6 && \
  pip install pep8==1.6.2 && \
  pip install pyflakes==0.8.1 && \
  pip install pyandoc==0.0.1 && \
  pip install sphinx-me==0.2.1

COPY . /pilbox

WORKDIR /pilbox

CMD ["python", "-m", "pilbox.app", "--debug"]
