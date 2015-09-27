import twitter
from ConfigParser import ConfigParser

config = ConfigParser()
config.read('config.ini')
CONSUMER_KEY = config.get('twitter', 'consumer_key')
CONSUMER_SECRET = config.get('twitter', 'consumer_secret')
OAUTH_TOKEN = config.get('twitter', 'oauth_token')
OAUTH_TOKEN_SECRET = config.get('twitter', 'oauth_token_secret')

def get_api():
    auth = twitter.oauth.OAuth(OAUTH_TOKEN, OAUTH_TOKEN_SECRET, CONSUMER_KEY, CONSUMER_SECRET)
    api = twitter.Twitter(auth=auth)
    return api