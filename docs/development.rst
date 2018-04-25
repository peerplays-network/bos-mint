Development Environment
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: sh

   $ apt-get install -y python3 python3-pip libmysqlclient-dev libssl-dev npm
   $ npm install -g bower

Install virtual environemnt user either one of the following 

.. code-block:: sh

   $ pip3 install virtualenv # should always works
   $ apt-get install python-virtualenv # Ubuntu 14.04 
   $ apt-get install virtualenv  # Ubuntu 16.04 
	
Install static files

.. code-block:: sh
	
   $ cd app
   $ bower install

Run the development server

.. code-block:: sh
	
	$ run_dev_server.sh
	
The manual intervention module is then available at
	
.. code-block:: sh

	http://localhost:5000/overview
	
For documentation of usage please look inside the scripts. To add the
init accounts please use

.. code-block:: js
	
	5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtP79zkvFD3

Scripts
~~~~~~~

* ``setup.sh``: Ensures that the given command is executed within a virtual environment
* ``run_dev_server.sh``: Starts the manual intervention module via flask development webservice 
