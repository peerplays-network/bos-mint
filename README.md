## Peerplays BOS - Bookie Oracle Software Suite - Manual Intervention Module

The purpose of these tools is to serve the witnesses and assist them
with their regular ground work of managing events on the PeerPlays
blockchain.

## Development use
Clone the develop branch from the repository locally
	git clone -b remote git@bitbucket.org:peerplaysblockchain/bookied-ui.git

Install 
	- python 3 or higher
	- virtualenv module

To run the development server execute
	run_dev_server.sh
	
The manual intervention module is then available at
	http://localhost:5000/overview
	
For documentation of usage please look inside the scripts. 
	
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
