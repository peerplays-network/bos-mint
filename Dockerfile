FROM ubuntu:17.04
 
# Update OS
RUN apt-get update
RUN apt-get -y upgrade
RUN apt-get install -y python3 python3-dev python3-pip libmysqlclient-dev libssl-dev git
 
# Create app directory
RUN mkdir /app
ADD requirements.txt /app

# Install app requirements
RUN pip3 install -r /app/requirements.txt

# Install app
ADD . /app
 
# Set the default directory for our environment
ENV HOME /app
WORKDIR /app
 
# Expose port 8000 for uwsgi
EXPOSE 8000

# Make settings persitent
VOLUME ["/app"]
 
ENTRYPOINT ["uwsgi", "--ini", "/app/uwsgi.ini"]
