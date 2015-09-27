# Examples from Mining the Social Web, section 3

from linkedin import linkedin # pip install python-linkedin
from ConfigParser import ConfigParser

config = ConfigParser()
config.read('config.ini')
CONSUMER_KEY = config.get('linkedin', 'client_id')
CONSUMER_SECRET = config.get('linkedin', 'client_secret')
RETURN_URL = config.get('linkedin', 'callback_URL')
TOKEN = config.get('linkedin', 'oauth2_access_token')

application = linkedin.LinkedInApplication(token=TOKEN)
print application.get_profile()
print application.get_connections()

