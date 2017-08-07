# Setup

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

# SQL Database

    CREATE DATABASE {database};
    CREATE USER '{user}'@'localhost' IDENTIFIED BY '{password}';
    GRANT ALL ON {database}.* TO '{user}'@'localhost';
    FLUSH PRIVILEGES;

    # set localhost=% .. to allow outside connections

# Manage setup

    python manage.py install
    python manage.py db init
    python manage.py db migrate
