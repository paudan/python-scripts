import requests
import json
import sys
from github import Github
from ConfigParser import ConfigParser

# Set utf-8 encoding as default
reload(sys)
sys.setdefaultencoding('utf8')

config = ConfigParser()
config.read('config.ini')
username = config.get('github', 'username')
password = config.get('github', 'password')

# Note that credentials will be transmitted over a secure SSL connection
url = 'https://api.github.com/authorizations'
note = 'Mining the Social Web, 2nd Ed.'
post_data = {'scopes':['repo'],'note': note }

response = requests.post(url, auth = (username, password), data = json.dumps(post_data), )

print "API response:", response.text
if response.json()['errors']:
    print response.json()['errors'][0]['code']
else:
    print "Your OAuth token is", response.json()['token']

# An unauthenticated request that doesn't contain an ?access_token=xxx query string
url = "https://api.github.com/repos/ptwobrussell/Mining-the-Social-Web/stargazers"
response = requests.get(url)
print json.dumps(response.json()[0], indent=1)
print
for (k,v) in response.headers.items():
    print k, "=>", v