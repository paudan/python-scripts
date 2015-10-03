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

MONGO_DIR = "C:\\Program Files\\MongoDB\\Server\\3.0\\bin\\"

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


def query_enron_database():
    # Connects to the MongoDB server running on localhost:27017 by default
    client = pymongo.MongoClient()
    # Get a reference to the enron database
    db = client.enron
    # Reference the mbox collection in the Enron database
    mbox = db.mbox

    # The number of messages in the collection
    print "Number of messages in mbox:", mbox.count()
    print

    # Display the message as pretty-printed JSON. The use of the custom serializer
    # supplied by PyMongo is necessary in order to handle the date field that is
    # provided as a datetime.datetime tuple.
    print "A message:"
    print json.dumps(mbox.find_one(), indent=1, default=json_util.default)

    # Create a small date range here of one day
    start_date = dt(2001, 4, 1)
    end_date = dt(2001, 4, 2)

    # Query the database with the highly versatile "find" command,
    msgs = [msg for msg in mbox.find({"Date": {
        "$lt": end_date,
        "$gt": start_date
    }
    }).sort("date")]
    print "Messages from a query by date range:"
    print json.dumps(msgs, indent=1, default=json_util.default)

    # Get senders and receivers and analyze them
    senders = [i for i in mbox.distinct("From")]
    receivers = [i for i in mbox.distinct("To")]
    cc_receivers = [i for i in mbox.distinct("Cc")]
    bcc_receivers = [i for i in mbox.distinct("Bcc")]
    print "Num Senders:", len(senders)
    print "Num Receivers:", len(receivers)
    print "Num CC Receivers:", len(cc_receivers)
    print "Num BCC Receivers:", len(bcc_receivers)

    senders = set(senders)
    receivers = set(receivers)
    cc_receivers = set(cc_receivers)
    bcc_receivers = set(bcc_receivers)
    # Find the number of senders who were also direct receivers
    senders_intersect_receivers = senders.intersection(receivers)
    # Find the senders that didn't receive any messages
    senders_diff_receivers = senders.difference(receivers)
    # Find the receivers that didn't send any messages
    receivers_diff_senders = receivers.difference(senders)
    # Find the senders who were any kind of receiver by first computing the union of all types of receivers
    all_receivers = receivers.union(cc_receivers, bcc_receivers)
    senders_all_receivers = senders.intersection(all_receivers)

    print "Num senders in common with receivers:", len(senders_intersect_receivers)
    print "Num senders who didn't receive:", len(senders_diff_receivers)
    print "Num receivers who didn't send:", len(receivers_diff_senders)
    print "Num senders in common with *all* receivers:", len(senders_all_receivers)

    # Finding senders and receivers of messages who were Enron employees
    senders = [i for i in mbox.distinct("From") if i.lower().find("@enron.com") > -1]
    receivers = [i for i in mbox.distinct("To") if i.lower().find("@enron.com") > -1]
    cc_receivers = [i for i in mbox.distinct("Cc") if i.lower().find("@enron.com") > -1]
    bcc_receivers = [i for i in mbox.distinct("Bcc") if i.lower().find("@enron.com") > -1]

    print "Enron employees:"
    print "Num Senders:", len(senders)
    print "Num Receivers:", len(receivers)
    print "Num CC Receivers:", len(cc_receivers)
    print "Num BCC Receivers:", len(bcc_receivers)

    # Counting sent/received messages for particular email addresses
    aliases = ["kenneth.lay@enron.com", "ken_lay@enron.com", "ken.lay@enron.com",
               "kenneth_lay@enron.net", "klay@enron.com"]  # More possibilities?
    to_msgs = [msg for msg in mbox.find({"To": {"$in": aliases}})]
    from_msgs = [msg for msg in mbox.find({"From": {"$in": aliases}})]
    print "Number of message sent to:", len(to_msgs)
    print "Number of messages sent from:", len(from_msgs)

    FROM = "kenneth.lay@enron.com"
    # Get the recipient lists for each message
    recipients_per_msg = list(db.mbox.aggregate([
        {"$match": {"From": re.compile(r".*{0}.*".format(FROM), re.IGNORECASE)}},
        {"$project": {"From": 1, "To": 1}},
        {"$group": {"_id": "$From", "recipients": {"$addToSet": "$To"}}}
    ]))
    recipients_per_message = recipients_per_msg[0]['recipients']

    # Collapse the lists of recipients into a single list
    all_recipients = [recipient for message in recipients_per_message for recipient in message]
    # Calculate the number of recipients per sent message and sort
    recipients_per_message_totals = sorted([len(recipients)
                                            for recipients in recipients_per_message])

    # Demonstrate how to use $unwind followed by $group to collapse the recipient lists into
    # a single list (with no duplicates per the $addToSet operator)
    unique_rec = list(db.mbox.aggregate([
        {"$match": {"From": re.compile(r".*{0}.*".format(FROM), re.IGNORECASE)}},
        {"$project": {"From": 1, "To": 1}},
        {"$unwind": "$To"},
        {"$group": {"_id": "From", "recipients": {"$addToSet": "$To"}}}
    ]))
    unique_recipients = unique_rec[0]['recipients']

    print all_recipients
    print "Num total recipients on all messages:", len(all_recipients)
    print "Num recipients for each message:", recipients_per_message_totals
    print "Num unique recipients", len(unique_recipients)


def create_mongo_index():
    client = pymongo.MongoClient()
    db = client.enron
    mbox = db.mbox
    mbox.create_index([("$**", "text")], name="TextIndex")
    # Get the collection stats (collstats) on a collection named "mbox"
    print json.dumps(db.command("collstats", "mbox"), indent=1)
    print json.dumps(db.command("text", "mbox", search="raptor", limit=1),
                     indent=1, default=json_util.default)


def message_counts():
    client = pymongo.MongoClient()
    db = client.enron
    mbox = db.mbox
    results = list(mbox.aggregate([
        {"$project": {
            "_id": 0,
            "DateBucket": {
                "year": {"$year": "$Date"},
                "month": {"$month": "$Date"},
                "day": {"$dayOfMonth": "$Date"},
                "hour": {"$hour": "$Date"},
            }
        }
        },
        {"$group": {
            # Group by year and date by using these fields for the key.
            "_id": {"year": "$DateBucket.year", "month": "$DateBucket.month"},
            # Increment the sum for each group by 1 for every document that's in it
            "num_msgs": {"$sum": 1}
        }
        },
        {"$sort": {"_id.year": 1, "_id.month": 1} }
    ]))

    pt = PrettyTable(field_names=['Year', 'Month', 'Num Msgs'])
    pt.align['Num Msgs'], pt.align['Month'] = 'r', 'r'
    [pt.add_row([result['_id']['year'], result['_id']['month'], result['num_msgs']])
     for result in results]
    print pt


def cleanContent(msg):
    # Decode message from "quoted printable" format
    msg = quopri.decodestring(msg)
    try:
        soup = BeautifulSoup(msg)
    except:
        return ''
    return ''.join(soup.findAll(text=True))

def jsonifyMessage(msg):
    json_msg = {'parts': []}
    for (k, v) in msg.items():
        json_msg[k] = v.decode('utf-8', 'ignore')
    for k in ['To', 'Cc', 'Bcc']:
        if not json_msg.get(k):
            continue
        json_msg[k] = json_msg[k].replace('\n', '').replace('\t', '')\
                                 .replace('\r', '').replace(' ', '')\
                                 .decode('utf-8', 'ignore').split(',')

    for part in msg.walk():
        json_part = {}
        if part.get_content_maintype() == 'multipart':
            continue

        json_part['contentType'] = part.get_content_type()
        if not part.is_multipart():
            content = part.get_payload(decode=False).decode('utf-8', 'ignore')
        else:
            content = ''.join([x.as_string().decode('utf-8', 'ignore') for x in part.get_payload(decode=False)])
        json_part['content'] = cleanContent(content)
        json_msg['parts'].append(json_part)

    # Finally, convert date from asctime to milliseconds since epoch using the
    # $date descriptor so it imports "natively" as an ISODate object in MongoDB.
    then = parse(json_msg['Date'])
    millis = int(time.mktime(then.timetuple())*1000 + then.microsecond/1000)
    json_msg['Date'] = {'$date' : millis}

    return json_msg


# read_messages('data/northpole.mbox')
# create_json_file('data/enron.mbox')
# mongo_cmd('enron', 'db.mbox.stats()')
# query_enron_database()
# create_mongo_index()
# message_counts()