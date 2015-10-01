# Examples from Mining the Social Web, section 3

from linkedin import linkedin # pip install python-linkedin
import json
from ConfigParser import ConfigParser

config = ConfigParser()
config.read('config.ini')
CONSUMER_KEY = config.get('linkedin', 'client_id')
CONSUMER_SECRET = config.get('linkedin', 'client_secret')
RETURN_URL = config.get('linkedin', 'callback_URL')
TOKEN = config.get('linkedin', 'oauth2_access_token')

application = linkedin.LinkedInApplication(token=TOKEN)
print application.get_profile()

my_positions = application.get_profile(selectors=['positions'])
print json.dumps(my_positions, indent=1)

my_positions = application.get_profile(selectors=['positions:(company:(name,industry,id))'])
print json.dumps(my_positions, indent=1)

