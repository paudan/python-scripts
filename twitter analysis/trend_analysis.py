import twitter_login
import json
import codecs

twitter_api = twitter_login.get_api()
# Retrieving trends
# The Yahoo! Where On Earth ID for the entire world is 1.
# See https://dev.twitter.com/docs/api/1.1/get/trends/place and
# http://developer.yahoo.com/geo/geoplanet/
WORLD_WOE_ID = 1
US_WOE_ID = 23424977
# initiates an HTTP call to GET https://api.twitter.com/1.1/trends/place.json?id=1
# world_trends = twitter_api.trends.place(_id=WORLD_WOE_ID)
# us_trends = twitter_api.trends.place(_id=US_WOE_ID)
# Serializing results as unicode JSON files
# with io.open('world_trends.json', 'w', encoding='utf-8') as f:
#   f.write(unicode(json.dumps(world_trends, ensure_ascii=False, indent=1)))
# with io.open('us_trends.json', 'w', encoding='utf-8') as f:
#   f.write(unicode(json.dumps(us_trends, ensure_ascii=False, indent=1)))
# De-serializing results from unicode JSON files
with codecs.open('world_trends.json','r','utf8') as f:
    world_trends = json.load(f)
with codecs.open('us_trends.json','r','utf8') as f:
    us_trends = json.load(f)
print json.dumps(world_trends, ensure_ascii=False, encoding='utf8', indent=1).encode('utf8')
print
print json.dumps(world_trends, ensure_ascii=False, encoding='utf8', indent=1).encode('utf8')

world_trends_set = set([trend['name'] for trend in world_trends[0]['trends']])
us_trends_set = set([trend['name'] for trend in us_trends[0]['trends']])
common_trends = world_trends_set.intersection(us_trends_set)
print 'Common trends'
print common_trends