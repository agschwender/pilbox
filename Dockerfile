# This file describes how to build pilbox into a runnable linux container
# with all dependencies installed.
#
# To build:
# 1) Install docker (http://docker.io)
# 2) Clone pilbox repo if you haven't already:
#        git clone https://github.com/agschwender/pilbox.git
# 3) Build: cd pilbox && docker build .
# 4) Run: docker run -p :80 -p :8080 -p :8888 -t <imageid>
#
# VERSION		0.2
# DOCKER-VERSION	0.4.0

from        ubuntu:12.04
run         echo "deb http://archive.ubuntu.com/ubuntu precise main universe" > /etc/apt/sources.list
run         apt-get -y update

# List maintainers
maintainer  joe@tanga.com
maintainer  adam.gschwender@gmail.com

# Install required packages
run         apt-get -y install libjpeg-dev libfreetype6-dev zlib1g-dev
run         apt-get -y install libwebp-dev liblcms1-dev
run         apt-get -y install python-dev python-pip python-opencv python-numpy
run         apt-get -y install nginx-light supervisor varnish
run         pip install --use-mirrors Pillow==2.1.0 tornado==3.1 coverage==3.6

# Add directories
run         mkdir -p /var/log/supervisor
add         . /pilbox

# Add system configurations
add         ./docker/varnish-profile.sh /etc/default/varnish
add         ./docker/varnish.vcl /etc/varnish/default.vcl
add         ./docker/varnish.sh /usr/local/bin/varnish.sh
run         chmod ug+x /usr/local/bin/varnish.sh
add         ./docker/nginx.conf /etc/nginx/nginx.conf
add         ./docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
run         touch /pilbox/config/default

# Expose ports
expose 80
expose 8080
expose 8888

# Start supervisor
cmd         ["/usr/bin/supervisord", "-n"]
