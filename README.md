## Peerplays Bookied-UI

The purpose of these tools is to serve the witnesses and assist them
with their regular ground work of managing events on the PeerPlays
blockchain.

## Setup

### Setup Python Environment

    pip3 install uwsgi virtualenv --user
    virtualenv env
    source env/bin/activate
    pip3 install -r requirements.txt

## Run

    ./manage web
    (open browser with http://localhost:5000)


# Docker

## Build and Run Docker Container

    $ cd bookied-ui
    $ docker build -t boss:latest .
    $ docker-compose up

.. then open browser with URL:

    http://localhost:8000
