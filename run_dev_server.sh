#!/usr/bin/env bash

source ./setup.sh

# install bower packages
pushd app
bower install
popd

function run_dev_server {
	python manage.py web
}

eval_in_virtual_environment run_dev_server
