from bos_mint import app
from flask import Flask
from flask.ext.testing import LiveServerTestCase 
import urllib


# Testing with LiveServer
class TestGenericNew(LiveServerTestCase):
    
    # if the create_app is not implemented NotImplementedError will be raised
    def create_app(self):
        app.config['TESTING'] = True
        return app 
    
    def test_flask_application_is_up_and_running(self):
        c = app.test_client()
        c.get('/overview')
        
