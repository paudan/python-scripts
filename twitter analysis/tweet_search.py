import twitter_login
import json
from matplotlib.pyplot import *
from collections import Counter
from prettytable import PrettyTable

twitter_api = twitter_login.get_api()

q = '#basketball'
count = 100
# See https://dev.twitter.com/docs/api/1.1/get/search/tweets
search_results = twitter_api.search.tweets(q=q, count=count)
statuses = search_results['statuses']
# Iterate through 5 more batches of results by following the cursor
for _ in range(5):
    print "Length of statuses", len(statuses)
    try:
        next_results = search_results['search_metadata']['next_results']
    except KeyError, e: # No more results when next_results doesn't exist
        break
    # Create a dictionary from next_results, which has the following form:
    # ?max_id=313519052523986943&q=NCAA&include_entities=1
    kwargs = dict([ kv.split('=') for kv in next_results[1:].split("&") ])
    search_results = twitter_api.search.tweets(**kwargs)
    statuses += search_results['statuses']
# Show one sample search result by slicing the list...
print json.dumps(statuses[0], indent=1)

# Extracting text, screen names, and hashtags from tweets
status_texts = [ status['text'] for status in statuses ]
screen_names = [ user_mention['screen_name'] for status in statuses
                 for user_mention in status['entities']['user_mentions'] ]
hashtags = [ hashtag['text'] for status in statuses for hashtag in status['entities']['hashtags'] ]
# Compute a collection of all words from all tweets
words = [w for t in status_texts for w in t.split()]
# Explore the first 5 items for each...
print json.dumps(status_texts[0:5], indent=1)
print json.dumps(screen_names[0:5], indent=1)
print json.dumps(hashtags[0:5], indent=1)
print json.dumps(words[0:5], indent=1)

# Creating a basic frequency distribution from the words in tweets
for label, data in (('Word', words), ('Screen Name', screen_names), ('Hashtag', hashtags)):
    pt = PrettyTable(field_names=[label, 'Count'])
    c = Counter(data)
    [ pt.add_row(kv) for kv in c.most_common()[:10] ]
    pt.align[label], pt.align['Count'] = 'l', 'r' # Set column alignment
    print pt

# Calculating lexical diversity
def lexical_diversity(tokens):
    return 1.0*len(set(tokens))/len(tokens)

# A function for computing the average number of words per tweet
def average_words(statuses):
    total_words = sum([ len(s.split()) for s in statuses ])
    return 1.0*total_words/len(statuses)

print "Lexical diversity of words: ", lexical_diversity(words)
print "Lexical diversity of screen names: ", lexical_diversity(screen_names)
print "Lexical diversity of hashtags: ", lexical_diversity(hashtags)
print "average number of words per tweet: ", average_words(status_texts)

# Finding the most popular retweets
retweets = [(status['retweet_count'],status['retweeted_status']['user']['screen_name'],
             status['text']) for status in statuses if status.has_key('retweeted_status')]
# Slice off the first 5 from the sorted results and display each item in the tuple
pt = PrettyTable(field_names=['Count', 'Screen Name', 'Text'])
[ pt.add_row(row) for row in sorted(retweets, reverse=True)[:5] ]
pt.max_width['Text'] = 50
pt.align= 'l'
print pt

# Plotting frequencies of words and histograms
word_counts = sorted(Counter(words).values(), reverse=True)
loglog(word_counts)
ylabel("Frequency")
xlabel("Word Rank")
show()

for label, data in (('Words', words), ('Screen Names', screen_names), ('Hashtags', hashtags)):
    c = Counter(data)
    hist(c.values())
    title(label)
    ylabel("Number of items in bin")
    xlabel("Bins (number of times an item appeared)")
    show()

counts = [count for count, _, _ in retweets]
hist(counts)
title("Retweets")
xlabel('Bins (number of times retweeted)')
ylabel('Number of tweets in bin')
show()

print counts