## Peerplays BOS - Bookie Oracle Software Suite - Manual Intervention Module

The purpose of these tools is to serve the witnesses and assist them
with their regular ground work of managing events on the PeerPlays
blockchain.

## Development use
Clone the develop branch from the repository locally
	git clone -b remote git@bitbucket.org:peerplaysblockchain/bookied-ui.git

Install environment
	
	$ apt-get install -y python3 python3-pip libmysqlclient-dev libssl-dev npm
	$ npm install -g bower

Install virtual environemnt user either one of the following 

	$ pip3 install virtualenv # should always works
	$ apt-get install python-virtualenv # Ubuntu 14.04 
	$ apt-get install virtualenv  # Ubuntu 16.04 
	
Install static files
	
	$ cd app
	$ bower install

Run the development server
	
	$ run_dev_server.sh
	
The manual intervention module is then available at
	
	http://localhost:5000/overview
	
For documentation of usage please look inside the scripts. To add the init accounts please use
	
	5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtP79zkvFD3
	
### Description of scripts

setup.sh
	Ensures that the given command is executed within a virtual environment

run_dev_server.sh
	Starts the manual intervention module via flask development webservice 
	
## Docker

### Build and Run Docker Container

    $ cd bookied-ui
    $ docker build -t boss:latest .
    $ docker-compose up

.. then open browser with URL:

    http://localhost:8000
