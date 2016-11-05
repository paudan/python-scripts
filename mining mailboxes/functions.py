import mailbox
import email
import json
import sys, os
import quopri
import time
import re
from datetime import datetime as dt
from BeautifulSoup import BeautifulSoup
from dateutil.parser import parse
from prettytable import PrettyTable
import envoy  # pip install envoy
import pymongo  # pip install pymongo
from bson import json_util  # Comes with pymongo

MONGO_DIR = "C:\\Program Files\\MongoDB\\Server\\3.2\\bin\\"

"""
A routine that makes a ton of simplifying assumptions about converting an mbox message into a Python object
given the nature of the northpole.mbox file in order to demonstrate the basic parsing of an mbox with mail
# utilities
"""


def objectify_message(msg):
    # Map in fields from the message
    o_msg = dict([(k, v) for (k, v) in msg.items()])
    # Assume one part to the message and get its content and its content type
    part = [p for p in msg.walk()][0]
    o_msg['contentType'] = part.get_content_type()
    o_msg['content'] = part.get_payload()
    return o_msg


"""
Create an mbox that can be iterated over and transform each of its messages to a convenient JSON representation
"""
def read_messages(mbox):
    mbox = mailbox.UnixMailbox(open(mbox, 'rb'), email.message_from_file)
    messages = []
    while 1:
        msg = mbox.next()
        if msg is None: break
        messages.append(objectify_message(msg))
    print json.dumps(messages, indent=1)


def cleanContent(msg):
    # Decode message from "quoted printable" format, but first
    # re-encode, since decodestring will try to do a decode of its own
    msg = quopri.decodestring(msg.encode('utf-8'))

    # Strip out HTML tags, if any are present.
    # Bail on unknown encodings if errors happen in BeautifulSoup.
    try:
        soup = BeautifulSoup(msg)
    except:
        return ''
    return ''.join(soup.findAll(text=True))


# There's a lot of data to process, and the Pythonic way to do it is with a
# generator. See http://wiki.python.org/moin/Generators.
# Using a generator requires a trivial encoder to be passed to json for object
# serialization.

class Encoder(json.JSONEncoder):
    def default(self, o): return list(o)


# The generator itself...
def gen_json_msgs(mb):
    while 1:
        msg = mb.next()
        if msg is None:
            break
        yield jsonifyMessage(msg)


def jsonifyMessage(msg):
    json_msg = {'parts': []}
    for (k, v) in msg.items():
        json_msg[k] = v.decode('utf-8', 'ignore')

    # The To, Cc, and Bcc fields, if present, could have multiple items.
    # Note that not all of these fields are necessarily defined.
    for k in ['To', 'Cc', 'Bcc']:
        if not json_msg.get(k):
            continue
        json_msg[k] = json_msg[k].replace('\n', '').replace('\t', '').replace('\r', '') \
            .replace(' ', '').decode('utf-8', 'ignore').split(',')

    for part in msg.walk():
        json_part = {}
        if part.get_content_maintype() != 'text':
            print >> sys.stderr, "Skipping MIME content in JSONification ({0})".format(part.get_content_maintype())
            continue
        json_part['contentType'] = part.get_content_type()
        content = part.get_payload(decode=False).decode('utf-8', 'ignore')
        json_part['content'] = cleanContent(content)
        json_msg['parts'].append(json_part)

    # Finally, convert date from asctime to milliseconds since epoch using the
    # $date descriptor so it imports "natively" as an ISODate object in MongoDB
    then = parse(json_msg['Date'])
    millis = int(time.mktime(then.timetuple()) * 1000 + then.microsecond / 1000)
    json_msg['Date'] = {'$date': millis}
    return json_msg


def create_json_file(mbox):
    mbox = mailbox.UnixMailbox(open(mbox, 'rb'), email.message_from_file)
    # Write each message out as a JSON object on a separate line for easy import into MongoDB via mongoimport
    f = open(mbox + '.json', 'w')
    for msg in gen_json_msgs(mbox):
        if msg != None:
            f.write(json.dumps(msg, cls=Encoder) + '\n')
    f.close()
    print "All done"


def import_json_to_mongo():
    r = envoy.run([MONGO_DIR + 'mongoimport'])
    print r.std_out
    if r.std_err: print r.std_err
    data_file = os.path.join(os.getcwd(), 'data\\enron.mbox.json')
    r = envoy.run([MONGO_DIR + 'mongoimport --host localhost --db enron --collection mbox --file "%s"' % data_file])
    print r.std_out
    if r.std_err: print sys.stderr.write(r.std_err)


def mongo_cmd(db, cmd):
    r = envoy.run([MONGO_DIR + 'mongo %s --eval "printjson(%s)"' % (db, cmd,)])
    print r.std_out
    if r.std_err: print r.std_err


def create_mongo_index():
    client = pymongo.MongoClient()
    db = client.enron
    mbox = db.mbox
    mbox.create_index([("$**", "text")], name="TextIndex")
    # Get the collection stats (collstats) on a collection named "mbox"
    print json.dumps(db.command("collstats", "mbox"), indent=1)
    print json.dumps(db.command("text", "mbox", search="raptor", limit=1),
                     indent=1, default=json_util.default)


# read_messages('data/northpole.mbox')
# create_json_file('data/enron.mbox')
# mongo_cmd('enron', 'db.mbox.stats()')
# create_mongo_index()