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

    bos-mint start  --port 8001 --host localhost
    
The output that you see should contain

::

    2018-05-18 11:56:04,754 INFO      :  * Running on http://localhost:8001/ (Press CTRL+C to quit)

The above setup is basic and for development use. Going forward, a witness may want to deploy
UWSGI with parallel workers for the endpoint.

MINT is purposely run on localhost to restrict outside access. Securing a python flask application from malicious break in attempts is tedious and would be an ongoing effort. Recommendation is to access it via a SSH tunnel or through VPN.

Example for SSH tunnel: Assume BOS MINT is running on a remote server accessible via 1.2.3.4 and you have login credentials via SSH (password or pivate key access). On the local machine that you will be using to access MINT via a web browser open the tunnel

::

    ssh -f -N -L 8080:127.0.0.1:8001 yourusername@1.2.3.4

-f - send process to background
-N - do not send commands (if you need open ssh connections only for tunneling)
-L - port mapping (8080 port on your machine, 127.0.0.1:8001 - proxy to where MINT runs)

Now you can open mint in your browser using http://localhost:8080 address.

After starting MINT use your favorite desktop browser to access it and you will be asked to enter your witness key that will be stored encrypted in the 
local peerplays wallet. Please note that MINT is not optimized for mobile use yet.
