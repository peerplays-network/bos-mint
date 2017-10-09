## Peerplays Bookied-UI

The purpose of these tools is to serve the witnesses and assist them
with their regular ground work of managing events on the PeerPlays
blockchain.

## Setup

### Dependencies

    aptitude install python3-crypto \
                     python3-ecdsa \
                     mariadb-client \
                     mariadb-server \
                     mariadb-common \
                     libmariadbclient-dev \
                     pkg-config \
                     libffi6 \
                     libffi-dev \
                     autoconf \
                     libtool \
                     build-essential \
                     libssl-dev \
                     nginx \
                     supervisor

### Setup Python Environment

    pip3 install uwsgi virtualenv --user
    virtualenv env
    source env/bin/activate
    pip3 install -r requirements.txt

## Run

    ./manage web
    (open browser with http://localhost:5000)
