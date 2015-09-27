import twitter_login
import twitter
import sys

q = 'basketball' # Comma-separated list of terms
print >> sys.stderr, 'Filtering the public timeline for track="%s"' % (q,)
twitter_api = twitter_login.get_api()
twitter_stream = twitter.TwitterStream(auth=twitter_api.auth)
stream = twitter_stream.statuses.filter(track=q)
for tweet in stream:
    print tweet['text'].encode('utf8')

