import sys
import datetime
import time
import twitter  # pip install twitter
import pymongo  # pip install pymongo
from collections import Counter
import re
from urllib2 import URLError
from httplib import BadStatusLine
import twitter_text  # pip install twitter-text-py
from functools import partial
from sys import maxint
import numpy
import requests
import nltk  # pip install nltk
# from boilerpipe.extract import Extractor  # pip install boilerpipe
from twitter_login import get_api
from prettytable import PrettyTable


def save_to_mongo(data, mongo_db, mongo_db_coll, **mongo_conn_kw):
    # Connects to the MongoDB server running on localhost:27017 by default
    client = pymongo.MongoClient(**mongo_conn_kw)
    # Get a reference to a particular database
    db = client[mongo_db]
    # Reference a particular collection in the database
    coll = db[mongo_db_coll]
    # Perform a bulk insert and return the IDs
    return coll.insert(data)


def load_from_mongo(mongo_db, mongo_db_coll, return_cursor=False, criteria=None, projection=None, **mongo_conn_kw):
    client = pymongo.MongoClient(**mongo_conn_kw)
    db = client[mongo_db]
    coll = db[mongo_db_coll]
    if criteria is None:
        criteria = {}
    if projection is None:
        cursor = coll.find(criteria)
    else:
        cursor = coll.find(criteria, projection)
    # Returning a cursor is recommended for large amounts of data
    if return_cursor:
        return cursor
    else:
        return [item for item in cursor]


def twitter_search(twitter_api, q, max_results=200, **kw):
    # See https://dev.twitter.com/docs/api/1.1/get/search/tweets and
    # https://dev.twitter.com/docs/using-search for details on advanced
    # search criteria that may be useful for keyword arguments
    # See https://dev.twitter.com/docs/api/1.1/get/search/tweets
    search_results = twitter_api.search.tweets(q=q, count=100, **kw)
    statuses = search_results['statuses']
    # Iterate through batches of results by following the cursor until we
    # reach the desired number of results, keeping in mind that OAuth users
    # can "only" make 180 search queries per 15-minute interval. See
    # https://dev.twitter.com/docs/rate-limiting/1.1/limits for details.
    # A reasonable number of results is 1000, although that number of results may not exist for all queries.
    max_results = min(1000, max_results)
    for _ in range(10):
        try:
            next_results = search_results['search_metadata']['next_results']
        except KeyError, e:  # No more results when next_results doesn't exist
            break
        kwargs = dict([kv.split('=') for kv in next_results[1:].split("&")])
        search_results = twitter_api.search.tweets(**kwargs)
        statuses += search_results['statuses']
        if len(statuses) > max_results:
            break
    return statuses


def twitter_trends(twitter_api, woe_id):
    # Prefix ID with the underscore for query string parameterization.
    # Without the underscore, the twitter package appends the ID value
    # to the URL itself as a special-case keyword argument.
    return twitter_api.trends.place(_id=woe_id)


def get_time_series_data(api_func, mongo_db_name, mongo_db_coll,
                         secs_per_interval=60, max_intervals=15, **mongo_conn_kw):
    # Default settings of 15 intervals and 1 API call per interval ensure that
    # you will not exceed the Twitter rate limit.
    interval = 0
    while True:
        # A timestamp of the form "2013-06-14 12:52:07"
        now = str(datetime.datetime.now()).split(".")[0]
        ids = save_to_mongo(api_func(), mongo_db_name, mongo_db_coll + "-" + now)
        print >> sys.stderr, "Write {0} trends".format(len(ids))
        print >> sys.stderr.flush()
        time.sleep(secs_per_interval)  # seconds
        interval += 1
        if interval >= 15:
            break


def extract_tweet_entities(statuses):
    if len(statuses) == 0:
        return [], [], [], [], []
    screen_names = [user_mention['screen_name'] for status in statuses
                    for user_mention in status['entities']['user_mentions']]
    hashtags = [hashtag['text'] for status in statuses
                for hashtag in status['entities']['hashtags']]
    urls = [url['expanded_url'] for status in statuses for url in status['entities']['urls']]
    symbols = [symbol['text'] for status in statuses
               for symbol in status['entities']['symbols']]
    # In some circumstances (such as search results), the media entity may not appear
    if status['entities'].has_key('media'):
        media = [media['url'] for status in statuses for media in status['entities']['media']]
    else:
        media = []
    return screen_names, hashtags, urls, media, symbols


def find_popular_tweets(twitter_api, statuses, retweet_threshold=3):
    # You could also consider using the favorite_count parameter as part of
    # this heuristic, possibly using it to provide an additional boost to
    # popular tweets in a ranked formulation
    return [status for status in statuses if status['retweet_count'] > retweet_threshold]


def get_common_tweet_entities(statuses, entity_threshold=3):
    """
    Create a flat list of all tweet entities
    """
    tweet_entities = [e for status in statuses
                      for entity_type in extract_tweet_entities([status]) for e in entity_type]
    c = Counter(tweet_entities).most_common()
    # Compute frequencies
    return [(k, v) for (k, v) in c if v >= entity_threshold]


def get_rt_attributions(tweet):
    rt_patterns = re.compile(r"(RT|via)((?:\b\W*@\w+)+)", re.IGNORECASE)
    rt_attributions = []
    # Inspect the tweet to see if it was produced with /statuses/retweet/:id.
    # See https://dev.twitter.com/docs/api/1.1/get/statuses/retweets/%3Aid.
    if tweet.has_key('retweeted_status'):
        attribution = tweet['retweeted_status']['user']['screen_name'].lower()
        rt_attributions.append(attribution)
    # Also, inspect the tweet for the presence of "legacy" retweet patterns
    # such as "RT" and "via", which are still widely used for various reasons
    # and potentially very useful. See https://dev.twitter.com/discussions/2847
    # and https://dev.twitter.com/discussions/1748 for some details on how/why.
    try:
        rt_attributions += [mention.strip()
                            for mention in rt_patterns.findall(tweet['text'])[0][1].split()]
    except IndexError, e:
        pass
    # Filter out any duplicates
    return list(set([rta.strip("@").lower() for rta in rt_attributions]))


def make_twitter_request(twitter_api_func, max_errors=10, *args, **kw):
    """
    A nested helper function that handles common HTTPErrors. Return an updated
    value for wait_period if the problem is a 500 level error. Block until the
    # rate limit is reset if it's a rate limiting issue (429 error). Returns None
    # for 401 and 404 errors, which requires special handling by the caller.
    """

    def handle_twitter_http_error(e, wait_period=2, sleep_when_rate_limited=True):
        if wait_period > 3600:  # Seconds
            print >> sys.stderr, 'Too many retries. Quitting.'
            raise e
        # See https://dev.twitter.com/docs/error-codes-responses for common codes
        if e.e.code == 401:
            print >> sys.stderr, 'Encountered 401 Error (Not Authorized)'
            return None
        elif e.e.code == 404:
            print >> sys.stderr, 'Encountered 404 Error (Not Found)'
            return None
        elif e.e.code == 429:
            print >> sys.stderr, 'Encountered 429 Error (Rate Limit Exceeded)'
            if sleep_when_rate_limited:
                print >> sys.stderr, "Retrying in 15 minutes...ZzZ..."
                sys.stderr.flush()
                time.sleep(60 * 15 + 5)
                print >> sys.stderr, '...ZzZ...Awake now and trying again.'
                return 2
            else:
                raise e  # Caller must handle the rate limiting issue
        elif e.e.code in (500, 502, 503, 504):
            print >> sys.stderr, 'Encountered %i Error. Retrying in %i seconds' % \
                                 (e.e.code, wait_period)
            time.sleep(wait_period)
            wait_period *= 1.5
            return wait_period
        else:
            raise e
            # End of nested helper function

    wait_period = 2
    error_count = 0
    while True:
        try:
            return twitter_api_func(*args, **kw)
        except twitter.api.TwitterHTTPError, e:
            error_count = 0
            wait_period = handle_twitter_http_error(e, wait_period)
            if wait_period is None:
                return
        except URLError, e:
            error_count += 1
            print >> sys.stderr, "URLError encountered. Continuing."
            if error_count > max_errors:
                print >> sys.stderr, "Too many consecutive errors...bailing out."
                raise
        except BadStatusLine, e:
            error_count += 1
            print >> sys.stderr, "BadStatusLine encountered. Continuing."
            if error_count > max_errors:
                print >> sys.stderr, "Too many consecutive errors...bailing out."
                raise


def get_user_profile(twitter_api, screen_names=None, user_ids=None):
    # Must have either screen_name or user_id (logical xor)
    assert (screen_names != None) != (user_ids != None), \
        "Must have screen_names or user_ids, but not both"
    items_to_info = {}
    items = screen_names or user_ids
    while len(items) > 0:
        # Process 100 items at a time per the API specifications for /users/lookup.
        items_str = ','.join([str(item) for item in items[:100]])
        items = items[100:]
        if screen_names:
            response = make_twitter_request(twitter_api.users.lookup, screen_name=items_str)
        else:  # user_ids
            response = make_twitter_request(twitter_api.users.lookup, user_id=items_str)
        for user_info in response:
            if screen_names:
                items_to_info[user_info['screen_name']] = user_info
            else:  # user_ids
                items_to_info[user_info['id']] = user_info
        return items_to_info


def extract_text(txt):
    ex = twitter_text.Extractor(txt)
    print "Screen Names:", ex.extract_mentioned_screen_names_with_indices()
    print "URLs:", ex.extract_urls_with_indices()
    print "Hashtags:", ex.extract_hashtags_with_indices()


def get_friends_followers_ids(twitter_api, screen_name=None, user_id=None,
                              friends_limit=maxint, followers_limit=maxint):
    # Must have either screen_name or user_id (logical xor)
    assert (screen_name != None) != (user_id != None), \
        "Must have screen_name or user_id, but not both"

    get_friends_ids = partial(make_twitter_request, twitter_api.friends.ids, count=5000)
    get_followers_ids = partial(make_twitter_request, twitter_api.followers.ids, count=5000)
    friends_ids, followers_ids = [], []
    for twitter_api_func, limit, ids, label in [
        [get_friends_ids, friends_limit, friends_ids, "friends"],
        [get_followers_ids, followers_limit, followers_ids, "followers"]]:

        if limit == 0: continue

        cursor = -1
        while cursor != 0:

            # Use make_twitter_request via the partially bound callable...
            if screen_name:
                response = twitter_api_func(screen_name=screen_name, cursor=cursor)
            else:  # user_id
                response = twitter_api_func(user_id=user_id, cursor=cursor)

            if response is not None:
                ids += response['ids']
                cursor = response['next_cursor']

            print >> sys.stderr, 'Fetched {0} total {1} ids for {2}'.format(len(ids), label, (user_id or screen_name))
            if len(ids) >= limit or response is None:
                break

    return friends_ids[:friends_limit], followers_ids[:followers_limit]


def setwise_friends_followers_analysis(screen_name, friends_ids, followers_ids):
    friends_ids, followers_ids = set(friends_ids), set(followers_ids)
    print '{0} is following {1}'.format(screen_name, len(friends_ids))
    print '{0} is being followed by {1}'.format(screen_name, len(followers_ids))
    print '{0} of {1} are not following {2} back'.format(
        len(friends_ids.difference(followers_ids)),
        len(friends_ids), screen_name)
    print '{0} of {1} are not being followed back by {2}'.format(
        len(followers_ids.difference(friends_ids)),
        len(followers_ids), screen_name)
    print '{0} has {1} mutual friends'.format(
        screen_name, len(friends_ids.intersection(followers_ids)))


def harvest_user_timeline(twitter_api, screen_name=None, user_id=None, max_results=1000):
    assert (screen_name != None) != (user_id != None), \
        "Must have screen_name or user_id, but not both"
    kw = {  # Keyword args for the Twitter API call
            'count': 200,
            'trim_user': 'true',
            'include_rts': 'true',
            'since_id': 1
            }
    if screen_name:
        kw['screen_name'] = screen_name
    else:
        kw['user_id'] = user_id

    max_pages = 16
    results = []
    tweets = make_twitter_request(twitter_api.statuses.user_timeline, **kw)
    if tweets is None:  # 401 (Not Authorized) - Need to bail out on loop entry
        tweets = []
    results += tweets
    print >> sys.stderr, 'Fetched %i tweets' % len(tweets)

    page_num = 1
    if max_results == kw['count']:
        page_num = max_pages  # Prevent loop entry
    while page_num < max_pages and len(tweets) > 0 and len(results) < max_results:
        # Necessary for traversing the timeline in Twitter's v1.1 API:
        # get the next query's max-id parameter to pass in.
        # See https://dev.twitter.com/docs/working-with-timelines.
        kw['max_id'] = min([tweet['id'] for tweet in tweets]) - 1
        tweets = make_twitter_request(twitter_api.statuses.user_timeline, **kw)
        results += tweets
        print >> sys.stderr, 'Fetched %i tweets' % (len(tweets),)
        page_num += 1

    print >> sys.stderr, 'Done fetching tweets'
    return results[:max_results]


def crawl_followers(twitter_api, screen_name, limit=1000000, depth=2):
    seed_id = str(twitter_api.users.show(screen_name=screen_name)['id'])
    _, next_queue = get_friends_followers_ids(twitter_api, user_id=seed_id,
                                              friends_limit=0, followers_limit=limit)
    save_to_mongo({'followers': [_id for _id in next_queue]}, 'followers_crawl',
                  '{0}-follower_ids'.format(seed_id))
    d = 1
    while d < depth:
        d += 1
        (queue, next_queue) = (next_queue, [])
        for fid in queue:
            _, follower_ids = get_friends_followers_ids(twitter_api, user_id=fid,
                                                        friends_limit=0, followers_limit=limit)
            save_to_mongo({'followers': [_id for _id in follower_ids]},
                          'followers_crawl', '{0}-follower_ids'.format(fid))
            next_queue += follower_ids


def analyze_tweet_content(statuses):
    if len(statuses) == 0:
        print "No statuses to analyze"
        return

    # A nested helper function for computing lexical diversity
    def lexical_diversity(tokens):
        return 1.0 * len(set(tokens)) / len(tokens)

    # A nested helper function for computing the average number of words per tweet
    def average_words(statuses):
        total_words = sum([len(s.split()) for s in statuses])
        return 1.0 * total_words / len(statuses)

    status_texts = [status['text'] for status in statuses]
    screen_names, hashtags, urls, media, _ = extract_tweet_entities(statuses)

    # Compute a collection of all words from all tweets
    words = [w for t in status_texts for w in t.split()]

    print "Lexical diversity (words):", lexical_diversity(words)
    print "Lexical diversity (screen names):", lexical_diversity(screen_names)
    print "Lexical diversity (hashtags):", lexical_diversity(hashtags)
    print "Averge words per tweet:", average_words(status_texts)


# def summarize(url=None, html=None, n=100, cluster_threshold=5, top_sentences=5):
#     """
#     Adapted from "The Automatic Creation of Literature Abstracts" by H.P. Luhn
#     Parameters:
#     * n  - Number of words to consider
#     * cluster_threshold - Distance between words to consider
#     * top_sentences - Number of sentences to return for a "top n" summary
#     """
#     # Begin - nested helper function
#     def score_sentences(sentences, important_words):
#         scores = []
#         sentence_idx = -1
#         for s in [nltk.tokenize.word_tokenize(s) for s in sentences]:
#             sentence_idx += 1
#             word_idx = []
#
#             # For each word in the word list...
#             for w in important_words:
#                 try:
#                     # Compute an index for important words in each sentence
#                     word_idx.append(s.index(w))
#                 except ValueError, e:  # w not in this particular sentence
#                     pass
#
#             word_idx.sort()
#
#             # It is possible that some sentences may not contain any important words
#             if len(word_idx) == 0: continue
#
#             # Using the word index, compute clusters with a max distance threshold
#             # for any two consecutive words
#
#             clusters = []
#             cluster = [word_idx[0]]
#             i = 1
#             while i < len(word_idx):
#                 if word_idx[i] - word_idx[i - 1] < cluster_threshold:
#                     cluster.append(word_idx[i])
#                 else:
#                     clusters.append(cluster[:])
#                     cluster = [word_idx[i]]
#                 i += 1
#             clusters.append(cluster)
#             # Score each cluster. The max score for any given cluster is the score for the sentence.
#             max_cluster_score = 0
#             for c in clusters:
#                 significant_words_in_cluster = len(c)
#                 total_words_in_cluster = c[-1] - c[0] + 1
#                 score = 1.0 * significant_words_in_cluster \
#                         * significant_words_in_cluster / total_words_in_cluster
#                 if score > max_cluster_score:
#                     max_cluster_score = score
#             scores.append((sentence_idx, score))
#
#         return scores
#
#     # End - nested helper function
#
#     extractor = Extractor(extractor='ArticleExtractor', url=url, html=html)
#     # It's entirely possible that this "clean page" will be a big mess. YMMV.
#     # The good news is that the summarize algorithm inherently accounts for handling a lot of this noise.
#     txt = extractor.getText()
#     sentences = [s for s in nltk.tokenize.sent_tokenize(txt)]
#     normalized_sentences = [s.lower() for s in sentences]
#     words = [w.lower() for sentence in normalized_sentences for w in
#              nltk.tokenize.word_tokenize(sentence)]
#     fdist = nltk.FreqDist(words)
#     top_n_words = [w[0] for w in fdist.items()
#                    if w[0] not in nltk.corpus.stopwords.words('english')][:n]
#     scored_sentences = score_sentences(normalized_sentences, top_n_words)
#
#     # Summarization Approach 1:
#     # Filter out nonsignificant sentences by using the average score plus a
#     # fraction of the std dev as a filter
#     avg = numpy.mean([s[1] for s in scored_sentences])
#     std = numpy.std([s[1] for s in scored_sentences])
#     mean_scored = [(sent_idx, score) for (sent_idx, score) in scored_sentences
#                    if score > avg + 0.5 * std]
#
#     # Summarization Approach 2:
#     # Another approach would be to return only the top N ranked sentences
#     top_n_scored = sorted(scored_sentences, key=lambda s: s[1])[-top_sentences:]
#     top_n_scored = sorted(top_n_scored, key=lambda s: s[0])
#
#     # Decorate the post object with summaries
#     return dict(top_n_summary=[sentences[idx] for (idx, score) in top_n_scored],
#                 mean_scored_summary=[sentences[idx] for (idx, score) in mean_scored])


def analyze_favorites(twitter_api, screen_name, entity_threshold=2):
    favs = twitter_api.favorites.list(screen_name=screen_name, count=200)
    print "Number of favorites:", len(favs)
    # Figure out what some of the common entities are, if any, in the content
    common_entities = get_common_tweet_entities(favs, entity_threshold=entity_threshold)

    pt = PrettyTable(field_names=['Entity', 'Count'])
    [ pt.add_row(kv) for kv in common_entities ]
    pt.align['Entity'], pt.align['Count'] = 'l', 'r' # Set column alignment

    print
    print "Common entities in favorites..."
    print pt
    print
    print "Some statistics about the content of the favorities..."
    print
    analyze_tweet_content(favs)


# Sample usage
twitter_api = get_api()
print "OK"
analyze_favorites(twitter_api, "ptwobrussell")
