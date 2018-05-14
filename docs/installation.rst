************
Installation
************

.. code-block:: sh

   $ pip3 install bos-mint

Configuration
#############

Make sure your environment is prepared. MINT uses a local database which requires mysql setup. Assuming
a Ubuntu 16.04. machine, please install

sudo apt-get install mysql-server
sudo apt-get install libmysqlclient-dev

Additionally, you need a file ``config-bos-mint.yaml`` in your working directory with
modified content just like this:

.. literalinclude:: ../config-example.yaml

Execution
#########

.. code-block:: sh

    bos-mint start

After starting MINT you will be asked to enter your witness key that will be stored encrypted in the 
local peerplays wallet.