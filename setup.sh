#!/usr/bin/env bash

# this script provides a wrapper function to execute commands within 
# the python virtual environment
function eval_in_virtual_environment {
    VIRTUALENV_NAME=env

	# if the venv doesnt exist, create it
	# (it is assumed that the virtualenv command is 
	#  available, if not install it via
	#  pip install virtualinv)
    if [ ! -d ${VIRTUALENV_NAME} ]; then
      virtualenv env -p python3
    fi

	# activate, install user packages and re-activate
    source ${VIRTUALENV_NAME}/bin/activate
    pip install --upgrade pip
    pip install --upgrade wheel
    pip install -r requirements.txt
    deactivate
    source ${VIRTUALENV_NAME}/bin/activate
    
    # run user command
    echo "Running '$1' inside virtual environment..."
    $1
} 