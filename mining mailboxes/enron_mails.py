# Examples from Mining the Social Web, section 6

import sys
import urllib2
import time
import os
import email
import envoy  # pip install envoy
import re
from time import asctime
from dateutil.parser import parse # pip install python_dateutil

URL = "http://www.cs.cmu.edu/~enron/enron_mail_20150507.tgz"
DOWNLOAD_DIR = "data"

""" Downloads a file and displays a download status every 5 seconds """
def download(url, download_dir):
    file_name = url.split('/')[-1]
    u = urllib2.urlopen(url)
    f = open(os.path.join(download_dir, file_name), 'wb')
    meta = u.info()
    file_size = int(meta.getheaders("Content-Length")[0])
    print "Downloading: %s Bytes: %s" % (file_name, file_size)

    file_size_dl = 0
    block_sz = 8192
    last_update = time.time()
    while True:
        buffer = u.read(block_sz)
        if not buffer:
            break

        file_size_dl += len(buffer)
        f.write(buffer)
        download_status = r"%10d MB  [%3.2f%%]" % (file_size_dl / 1000000.0, file_size_dl * 100.0 / file_size)
        download_status = download_status + chr(8) * (len(download_status) + 1)
        if time.time() - last_update > 5:
            print download_status,
            sys.stdout.flush()
            last_update = time.time()
    f.close()
    return f.name


""" Extracts a gzipped tarfile. e.g. "$ tar xzf filename.tgz" """
def tar_xzf(f):
    # Call out to the shell for a faster decompression.
    # This will still take a while because Vagrant synchronizes
    # thousands of files that are extracted to the host machine
    r = envoy.run("tar xzf %s -C %s" % (f, DOWNLOAD_DIR))
    print r.std_out
    print r.std_err


def create_mbox_file(mbox, maildir):
    # Create a file handle that we'll be writing into...
    mbox = open(mbox, 'w')

    # Walk the directories and process any folder named 'inbox'
    for (root, dirs, file_names) in os.walk(maildir):

        if root.split(os.sep)[-1].lower() != 'inbox':
            continue
        # Process each message in 'inbox'
        for file_name in file_names:
            file_path = os.path.join(root, file_name)
            message_text = open(file_path).read()

            # Compute fields for the From_ line in a traditional mbox message
            _from = re.search(r"From: ([^\r]+)", message_text).groups()[0]
            _date = re.search(r"Date: ([^\r]+)", message_text).groups()[0]

            # Convert _date to the asctime representation for the From_ line
            _date = asctime(parse(_date).timetuple())
            msg = email.message_from_string(message_text)
            msg.set_unixfrom('From %s %s' % (_from, _date))
            mbox.write(msg.as_string(unixfrom=True) + "\n\n")

    mbox.close()

f = download(URL, DOWNLOAD_DIR)
print "Download complete: %s" % (f,)
tar_xzf(f)
print "Decompression complete"
print "Data is ready"
create_mbox_file('data/enron.mbox', DOWNLOAD_DIR + 'enron_data/maildir')