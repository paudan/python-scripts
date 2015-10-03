import imaplib
import xoauth2
import sys
import os
import email
import functions
import json
from ConfigParser import ConfigParser

# Set utf-8 encoding as default
reload(sys)
sys.setdefaultencoding('utf8')

config = ConfigParser()
config.read('config.ini')
email_address = config.get('gmail', 'gmail_account')
key = config.get('gmail', 'client_id')
secret = config.get('gmail', 'client_secret')
imap_server = config.get('gmail', 'imap_server')
imap_port = config.get('gmail', 'imap_port')
token = config.get('gmail', 'token')
refresh_token = config.get('gmail', 'refresh_token')

response = xoauth2.RefreshToken(key, secret, refresh_token)
token = response['access_token']
xoauth_string = xoauth2.GenerateOAuth2String(email_address, token, base64_encode=False)
conn = imaplib.IMAP4_SSL(imap_server)
conn.authenticate('XOAUTH2', lambda x: xoauth_string)

config.set('gmail', 'token', token)
with open('config.ini', 'wb') as configfile:
    config.write(configfile)

print conn.list()
conn.select('konferencijos')

Q = "conference"
# Consume a query from the user. This example illustrates searching by subject.
(status, data) = conn.search(None, '(SUBJECT "%s")' % (Q, ))
ids = data[0].split()

messages = []
for i in ids:
    try:
        (status, data) = conn.fetch(i, '(RFC822)')
        messages.append(email.message_from_string(data[0][1]))
    except Exception, e:
        print e
        print 'Print error fetching message %s. Skipping it.' % (i, )

print len(messages)
jsonified_messages = [functions.jsonifyMessage(m) for m in messages]

# Separate out the text content from each message so that it can be analyzed.
content = [p['content'] for m in jsonified_messages for p in m['parts']]

# Content can still be quite messy and contain line breaks and other quirks.
filename = os.path.join('data', email_address.split("@")[0] + '.gmail.json')
f = open(filename, 'w')
f.write(json.dumps(jsonified_messages))
f.close()

print >> sys.stderr, "Data written out to", f.name