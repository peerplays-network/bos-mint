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

   wget https://raw.githubusercontent.com/PBSA/bos-mint/master/config-example.yaml
   mv config-example.yaml config-bos-mint.yaml
   # modify config-bos-mint.yaml (add your own secret key)

Possible override values are described below:

.. include:: ../bos_mint/config-defaults.yaml
   :literal:

Running bos-mint
#########

.. code-block:: sh

    bos-mint start

After starting MINT you will be asked to enter your witness key that will be stored encrypted in the 
local peerplays wallet.