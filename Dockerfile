from ubuntu:12.04
maintainer joe@tanga.com
run echo "deb http://archive.ubuntu.com/ubuntu precise main universe" > /etc/apt/sources.list
run apt-get update
run apt-get upgrade -y
run apt-get install libjpeg-dev libfreetype6-dev zlib1g-dev libwebp-dev liblcms1-dev -y
run apt-get install python-dev -y
run apt-get install python-pip -y
run apt-get install python-opencv -y

# Not sure if these should be installed with pip or apt-get? Are the ones in apt new enough?
run pip install Pillow 
run pip install coverage
run pip install tornado
run pip install numpy

# TODO
# Start the application with the CMD command.
# Setup security keys 

