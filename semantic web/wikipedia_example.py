# Examples from Mining the Social Web, section 8

import webbrowser
import requests # pip install requests
from BeautifulSoup import BeautifulSoup # pip install BeautifulSoup

# XXX: Any URL containing a geo microformat...
URL = 'http://en.wikipedia.org/wiki/Kaunas'

req = requests.get(URL, headers={'User-Agent' : "Mining the Social Web"})
soup = BeautifulSoup(req.text)

geoTag = soup.find(True, 'geo')

if geoTag and len(geoTag) > 1:
    lat = geoTag.find(True, 'latitude').string
    lon = geoTag.find(True, 'longitude').string
    print 'Location is at', lat, lon
elif geoTag and len(geoTag) == 1:
    (lat, lon) = geoTag.string.split(';')
    (lat, lon) = (lat.strip(), lon.strip())
    print 'Location is at', lat, lon
else:
    print 'No location found'

google_maps_url = "http://maps.google.com/maps?q={0}+{1}&ie=UTF8&t=h&z=14&{0},{1}".format(lat, lon)
webbrowser.open(google_maps_url)