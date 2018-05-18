************
Installation
************

Install dependencies (as root/sudo)
##########################

::

    apt-get install libffi-dev libssl-dev python-dev python3-pip
    pip3 install virtualenv
    
Note that virtualenv is a best practice for python, but installation can also be on a user/global level.

Install databases (as root/sudo)
##########################

MINT uses a local sqllite database which requires mysql setup. Assuming
a Ubuntu 16.04. machine, please install

::

    sudo apt-get install mysql-server
    sudo apt-get install libmysqlclient-dev

Install bos-mint
##########################

For production use install bos-mint via pip3. Suggested is a seperate user

::

    cd ~
    mkdir bos-mint
    cd bos-mint
    virtualenv -p python3 env
    source env/bin/activate
    pip3 install bos-mint
    
For development use, checkout from github and install dependencies manually

::

    cd ~	
    git checkout https://github.com/pbsa/bos-mint
    cd bos-mint
    virtualenv -p python3 env
    source env/bin/activate
    pip3 install -r requirements.txt

Modify configuration
##########################

We now need to configure bos-auto.

::
   
   # basic mint configuration file
   wget https://raw.githubusercontent.com/PBSA/bos-mint/master/config-example.yaml
   mv config-example.yaml config-bos-mint.yaml
   # modify config-bos-mint.yaml (add your own peerplays node and secret key)

Defauilt config only requires as listed below:

.. include:: ../config-example.yaml
   :literal:
   
Possible override values are described below:

.. include:: ../bos_mint/config-defaults.yaml
   :literal:

Running bos-mint
#########
To run MINT in debug mode use

.. code-block:: sh

    bos-mint start  --port 8001 --host 0.0.0.0
    
The output that you see should contain

    2018-05-18 11:56:04,754 INFO      :  * Running on http://localhost:5000/ (Press CTRL+C to quit)

After starting MINT you will be asked to enter your witness key that will be stored encrypted in the 
local peerplays wallet.

The above setup is basic. Going forward, a witness may want to deploy
UWSGI with parallel workers for the endpoint, create a local socket and
hide it behind an SSL supported nginx.
