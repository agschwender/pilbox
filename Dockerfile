# This file describes how to build pilbox into a runnable linux container
# with all dependencies installed.
#
# To build:
# 1) Install docker (http://docker.io)
# 2) Clone pilbox repo if you haven't already:
#        git clone https://github.com/agschwender/pilbox.git
# 3) Build: cd pilbox && docker build .
# 4) Run ssh:
#        docker run -p 2222:22 -v `pwd`:/pilbox -t <imageid> ssh
# 5) Run ansible:
#        ansible-playbook -i provisioning/docker provisioning/playbook.yml
# 6) Run web:
#        docker run -p :80 -p :8080 -p :8888 -v `pwd`:/pilbox -t <imageid> web
#
# VERSION		0.3
# DOCKER-VERSION	0.4.0

from        ubuntu:12.04
run         apt-get -y install python-software-properties
run         echo "deb http://archive.ubuntu.com/ubuntu precise main universe" > /etc/apt/sources.list
run         apt-get -y update

# List maintainers
maintainer  joe@tanga.com
maintainer  adam.gschwender@gmail.com

# Install base container
run         groupadd admin
run         apt-get -y install openssh-server sudo
run         mkdir /var/run/sshd
add         ./provisioning/files/etc/sudoers /etc/
run         chown root:root /etc/sudoers && chmod 0440 /etc/sudoers
run         useradd -d /home/ansible -s /bin/bash -m ansible
run         echo "ansible:ansible" | chpasswd
run         usermod -a -G admin ansible
run         mkdir -p /home/ansible/.ssh
run         chown ansible:ansible /home/ansible/.ssh && chmod 0700 /home/ansible/.ssh
add         ./provisioning/files/usr/local/bin/docker-entry.sh /usr/local/bin/
run         chmod 0755 /usr/local/bin/docker-entry.sh
run         mkdir -p /pilbox/config && touch /pilbox/config/default


# Expose ports
expose      22
expose      80
expose      8080
expose      8888

# Entrypoint

entrypoint  ["/usr/local/bin/docker-entry.sh"]
cmd         ["web"]
