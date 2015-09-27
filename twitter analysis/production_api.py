# Example from Mining the Social Web, section 1

from flask import Flask, request        #pip install flask
import multiprocessing
from threading import Timer
from IPython.display import IFrame
from IPython.display import display
from IPython.display import Javascript as JS
import twitter
from twitter.oauth_dance import parse_oauth_tokens
from twitter.oauth import read_token_file, write_token_file
from ConfigParser import ConfigParser

config = ConfigParser()
config.read('config.ini')
CONSUMER_KEY = config.get('twitter', 'consumer_key')
CONSUMER_SECRET = config.get('twitter', 'consumer_secret')
oauth_callback = config.get('twitter', 'oauth_callback')
OAUTH_FILE = "twitter_oauth"

# Set up a callback handler for when Twitter redirects back to us after the user
# authorizes the app
webserver = Flask("TwitterOAuth")
@webserver.route("/oauth_helper")
def oauth_helper():
    oauth_verifier = request.args.get('oauth_verifier')
    # Pick back up credentials from ipynb_oauth_dance
    oauth_token, oauth_token_secret = read_token_file(OAUTH_FILE)
    _twitter = twitter.Twitter(
        auth=twitter.OAuth(oauth_token, oauth_token_secret, CONSUMER_KEY, CONSUMER_SECRET),
        format='', api_version=None)
    oauth_token, oauth_token_secret = parse_oauth_tokens(
    _twitter.oauth.access_token(oauth_verifier=oauth_verifier))
    # This web server only needs to service one request, so shut it down
    shutdown_after_request = request.environ.get('werkzeug.server.shutdown')
    shutdown_after_request()
    # Write out the final credentials that can be picked up after the following
    # blocking call to webserver.run().
    write_token_file(OAUTH_FILE, oauth_token, oauth_token_secret)
    return "%s %s written to %s" % (oauth_token, oauth_token_secret, OAUTH_FILE)

# To handle Twitter's OAuth 1.0a implementation, we'll just need to implement a
# custom "oauth dance" and will closely follow the pattern defined in
# twitter.oauth_dance.

def ipynb_oauth_dance():
    _twitter = twitter.Twitter(
        auth=twitter.OAuth('', '', CONSUMER_KEY, CONSUMER_SECRET),
        format='', api_version=None)
    oauth_token, oauth_token_secret = parse_oauth_tokens(_twitter.oauth.request_token(oauth_callback=oauth_callback))
    # Need to write these interim values out to a file to pick up on the callback
    # from Twitter that is handled by the web server in /oauth_helper
    write_token_file(OAUTH_FILE, oauth_token, oauth_token_secret)
    oauth_url = ('http://api.twitter.com/oauth/authorize?oauth_token=' + oauth_token)
    # Tap the browser's native capabilities to access the web server through a new
    # window to get user authorization
    display(JS("window.open('%s')" % oauth_url))

# After the webserver.run() blocking call, start the OAuth Dance that will
# ultimately cause Twitter to redirect a request back to it. Once that request
# is serviced, the web server will shut down and program flow will resume
# with the OAUTH_FILE containing the necessary credentials.
Timer(1, lambda: ipynb_oauth_dance()).start()
webserver.run(host='0.0.0.0')
# The values that are read from this file are written out at
# the end of /oauth_helper
oauth_token, oauth_token_secret = read_token_file(OAUTH_FILE)
# These four credentials are what is needed to authorize the application
auth = twitter.oauth.OAuth(oauth_token, oauth_token_secret, CONSUMER_KEY, CONSUMER_SECRET)
twitter_api = twitter.Twitter(auth=auth)
print twitter_api