# Examples from Mining the Social Web, section 1

from twitter_functions import *
import json
import twitter_login

# Mongo DB usage examples
q = 'basketball'
twitter_api = twitter_login.get_api()
results = twitter_search(twitter_api, q, max_results=10)
save_to_mongo(results, 'search_results', q)
load_from_mongo('search_results', q)

# Time series examples
WORLD_WOE_ID = 1
pp = partial(json.dumps, indent=1)
twitter_world_trends = partial(twitter_trends, get_api, WORLD_WOE_ID)
print pp(twitter_world_trends())
get_time_series_data(twitter_world_trends, 'time-series', 'twitter_world_trends')

# Extract tweet entities
statuses = twitter_search(twitter_api, q)
screen_names, hashtags, urls, media, symbols = extract_tweet_entities(statuses)
print json.dumps(screen_names[0:5], indent=1)
print json.dumps(hashtags[0:5], indent=1)
print json.dumps(urls[0:5], indent=1)
print json.dumps(media[0:5], indent=1)
print json.dumps(symbols[0:5], indent=1)

# Finding popular tweets
search_results = twitter_search(twitter_api, q, max_results=200)
popular_tweets = find_popular_tweets(twitter_api, search_results)
for tweet in popular_tweets:
    print tweet['text'].encode('utf8'), tweet['retweet_count']

# Finding most common tweet entities
search_results = twitter_search(twitter_api, q, max_results=100)
common_entities = get_common_tweet_entities(search_results)
print "Most common tweet entities"
from prettytable import PrettyTable
pt = PrettyTable(field_names=['Entity', 'Count'])
[ pt.add_row(kv) for kv in common_entities ]
pt.align['Entity'], pt.align['Count'] = 'l', 'r' # Set column alignment
print pt

# Extracting a retweet’s attribution
q = 'CrossFit'
tweet = twitter_api.statuses.show(_id=214746575765913602)
print get_rt_attributions(tweet)
print
tweet = twitter_api.statuses.show(_id=345723917798866944)
print get_rt_attributions(tweet)

# Twitter request processing with exceptions
response = make_twitter_request(twitter_api.users.lookup, screen_name="SocialWebMining")
print json.dumps(response, indent=1)

# Getting user information
print json.dumps(get_user_profile(twitter_api, screen_names=["SocialWebMining", "ptwobrussell"]), indent=1)
# print json.dumps(get_user_profile(twitter_api, user_ids=[132373965]), indent=1)

# Text extraction
extract_text("RT @SocialWebMining Mining 1M+ Tweets About #Syria http://wp.me/p3QiJd-1I")

# Get the number of friends and followers and perform their analysis
screen_name = "ptwobrussell"
friends_ids, followers_ids = get_friends_followers_ids(twitter_api,
                                                       screen_name=screen_name,
                                                       friends_limit=10,
                                                       followers_limit=10)
print friends_ids
print followers_ids
friends_ids, followers_ids = get_friends_followers_ids(twitter_api,screen_name=screen_name)
setwise_friends_followers_analysis(screen_name, friends_ids, followers_ids)

# Read user's tweets
tweets = harvest_user_timeline(twitter_api, screen_name="SocialWebMining", max_results=200)

# Find the followers (limit to 10)
screen_name = "timoreilly"
crawl_followers(twitter_api, screen_name, depth=1, limit=10)

# Summarization

sample_url = 'http://radar.oreilly.com/2013/06/phishing-in-facebooks-pond.html'
summary = summarize(url=sample_url)

# Alternatively, you can pass in HTML if you have it. Sometimes this approach may be
# necessary if you encounter mysterious urllib2.BadStatusLine errors. Here's how
# that would work:

# sample_html = requests.get(sample_url).text
# summary = summarize(html=sample_html)

print "-------------------------------------------------"
print "                'Top N Summary'"
print "-------------------------------------------------"
print " ".join(summary['top_n_summary'])
print
print
print "-------------------------------------------------"
print "             'Mean Scored' Summary"
print "-------------------------------------------------"
print " ".join(summary['mean_scored_summary'])

# Analyze favorites
analyze_favorites(twitter_api, "ptwobrussell")

