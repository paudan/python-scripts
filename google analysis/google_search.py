# Examples from Mining the Social Web, section 4

import json
import re
from ConfigParser import ConfigParser
import sys
import codecs
from os import path

from httplib2 import Http
from apiclient import discovery  # pip install google-api-python-client
from oauth2client import client, file, tools
from BeautifulSoup import BeautifulStoneSoup
import nltk

sys.stdout = codecs.getwriter('utf8')(sys.stdout)

config = ConfigParser()
config.read(path.join(path.dirname(path.realpath(__file__)), 'config.ini'))
API_KEY = config.get('config', 'api_key')


def auth_service():
    client_secrets = 'credentials.json'
    try:
        import argparse
        flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
    except ImportError:
        flags = None

    # Set up a Flow object to be used if we need to authenticate.
    flow = client.flow_from_clientsecrets(client_secrets,
                                          scope='https://www.googleapis.com/auth/plus.login',
                                          message=tools.message_if_missing(client_secrets))

    # Prepare credentials, and authorize HTTP object with them.
    # If the credentials don't exist or are invalid run through the native client
    # flow. The Storage object will ensure that if successful the good
    # credentials will get written back to a file.
    storage = file.Storage('gplus.dat')
    credentials = storage.get()
    if credentials is None or credentials.invalid:
        credentials = tools.run_flow(flow, storage, flags)
    http = credentials.authorize(http=Http())
    service = discovery.build('plus', 'v1', http=http)
    return service


def api_service():
    return discovery.build('plus', 'v1', http=Http(), developerKey=API_KEY)


def get_user_activity(user_id):
    if user_id == 'me':
        # Authentication required
        service = auth_service()
        person = service.people().get(userId=user_id).execute()
        print 'Got your ID: %s' % person['displayName']
    else:
        service = api_service()
    activity_feed = service.activities().list(userId=user_id, collection='public',
                                              maxResults='100'  # Max allowed per API
                                              ).execute()
    print json.dumps(activity_feed, indent=1)
    return activity_feed


def perform_query(query):
    service = api_service()
    people_feed = service.people().search(query=query).execute()
    print json.dumps(people_feed['items'], indent=1)


def clean_html(html):
    # First we remove inline JavaScript/CSS:
    cleaned = re.sub(r"(?is)<(script|style).*?>.*?(</\1>)", "", html.strip())
    # Then we remove html comments. This has to be done before removing regular
    # tags since comments can contain '>' characters.
    cleaned = re.sub(r"(?s)<!--(.*?)-->[\n]?", "", cleaned)
    # Next we can remove the remaining tags:
    cleaned = re.sub(r"(?s)<.*?>", " ", cleaned)
    # Finally, we deal with whitespace
    cleaned = re.sub(r"&nbsp;", " ", cleaned)
    cleaned = re.sub(r"  ", " ", cleaned)
    cleaned = re.sub(r"  ", " ", cleaned)
    return cleaned.strip()


def cleanHtml(html):
    if html is None or html == "": return ""
    return BeautifulStoneSoup(clean_html(html), convertEntities=BeautifulStoneSoup.HTML_ENTITIES).contents[0]


def parse_activities(user_id, max_results):
    service = auth_service()
    activity_feed = service.activities().list(
        userId=user_id,
        collection='public',
        maxResults='100'  # Max allowed per request
    )
    activity_results = []
    while activity_feed is not None and len(activity_results) < max_results:
        activities = activity_feed.execute()
        if 'items' in activities:
            for activity in activities['items']:
                if activity['object']['objectType'] == 'note' and \
                                activity['object']['content'] != '':
                    activity['title'] = cleanHtml(activity['title'])
                    activity['object']['content'] = cleanHtml(activity['object']['content'])
                    activity_results += [activity]
        # list_next requires the previous request and response objects
        activity_feed = service.activities().list_next(activity_feed, activities)

    # Write the output to a file for convenience
    f = open(user_id + '.json', 'w')
    f.write(json.dumps(activity_results, indent=1))
    f.close()

    print str(len(activity_results)), "activities written to", f.name


def tfidf_query(file, query_terms):
    data = json.loads(open(file).read())
    activities = [activity['object']['content'].lower().split() for activity in data \
                  if activity['object']['content'] != ""]

    tc = nltk.TextCollection(activities)

    relevant_activities = []
    for idx in range(len(activities)):
        score = 0
        for term in [t.lower() for t in query_terms]:
            score += tc.tf_idf(term, activities[idx])
        if score > 0:
            relevant_activities.append({'score': score, 'title': data[idx]['title'],
                                        'url': data[idx]['url']})

    # Sort by score and display results
    relevant_activities = sorted(relevant_activities,
                                 key=lambda p: p['score'], reverse=True)
    for activity in relevant_activities:
        print activity['title']
        print '\tLink: %s' % (activity['url'],)
        print '\tScore: %s' % (activity['score'],)
        print


def calculate_ranks(fname):
    data = json.loads(open(fname).read())
    all_content = " ".join([a['object']['content'] for a in data])
    tokens = all_content.split()
    text = nltk.Text(tokens)
    # Frequency analysis for words of interest
    fdist = text.vocab()
    # Common words that aren't stopwords
    [w for w in fdist.keys()[:100] \
     if w.lower() not in nltk.corpus.stopwords.words('english')]

    # Long words that aren't URLs
    [w for w in fdist.keys() if len(w) > 15 and not w.startswith("http")]

    # Number of URLs
    len([w for w in fdist.keys() if w.startswith("http")])

    # Enumerate the frequency distribution
    for rank, word in enumerate(fdist):
        print rank, word, fdist[word]


def cosine_similarity(fname):
    data = json.loads(open(fname).read())

    # Only consider content that's ~1000+ words.
    data = [post for post in json.loads(open(fname).read())
            if len(post['object']['content']) > 1000]

    all_posts = [post['object']['content'].lower().split() for post in data]
    tc = nltk.TextCollection(all_posts)

    # Compute a term-document matrix such that td_matrix[doc_title][term]
    # returns a tf-idf score for the term in the document
    td_matrix = {}
    for idx in range(len(all_posts)):
        post = all_posts[idx]
        fdist = nltk.FreqDist(post)

        doc_title = data[idx]['title']
        url = data[idx]['url']
        td_matrix[(doc_title, url)] = {}

        for term in fdist.iterkeys():
            td_matrix[(doc_title, url)][term] = tc.tf_idf(term, post)

    # Build vectors such that term scores are in the same positions...

    distances = {}
    for (title1, url1) in td_matrix.keys():

        distances[(title1, url1)] = {}
        (min_dist, most_similar) = (1.0, ('', ''))

        for (title2, url2) in td_matrix.keys():

            # Take care not to mutate the original data structures
            # since we're in a loop and need the originals multiple times

            terms1 = td_matrix[(title1, url1)].copy()
            terms2 = td_matrix[(title2, url2)].copy()

            # Fill in "gaps" in each map so vectors of the same length can be computed

            for term1 in terms1:
                if term1 not in terms2:
                    terms2[term1] = 0

            for term2 in terms2:
                if term2 not in terms1:
                    terms1[term2] = 0

            # Create vectors from term maps

            v1 = [score for (term, score) in sorted(terms1.items())]
            v2 = [score for (term, score) in sorted(terms2.items())]

            # Compute similarity amongst documents

            distances[(title1, url1)][(title2, url2)] = \
                nltk.cluster.util.cosine_distance(v1, v2)

            if url1 == url2:
                # print distances[(title1, url1)][(title2, url2)]
                continue

            if distances[(title1, url1)][(title2, url2)] < min_dist:
                (min_dist, most_similar) = (distances[(title1, url1)][(title2,
                                                                       url2)], (title2, url2))

        print '''Most similar to %s (%s)
    \t%s (%s)
    \tscore %f
    ''' % (title1, url1, most_similar[0], most_similar[1], 1 - min_dist)


def linkage_matrix(fname):
    from IPython.display import IFrame
    from IPython.core.display import display

    # Only consider content that's ~100+ words.
    data = [post for post in json.loads(open(fname).read())
            if len(post['object']['content']) > 1000]

    all_posts = [post['object']['content'].lower().split() for post in data]
    tc = nltk.TextCollection(all_posts)

    td_matrix = {}
    for idx in range(len(all_posts)):
        post = all_posts[idx]
        fdist = nltk.FreqDist(post)

        doc_title = data[idx]['title']
        url = data[idx]['url']
        td_matrix[(doc_title, url)] = {}

        for term in fdist.iterkeys():
            td_matrix[(doc_title, url)][term] = tc.tf_idf(term, post)
    distances = {}

    viz_links = []
    viz_nodes = [{'title': title, 'url': url} for (title, url) in td_matrix.keys()]

    foo = 0
    for vn in viz_nodes:
        vn.update({'idx': foo})
        foo += 1

    idx = dict(zip([vn['title'] for vn in viz_nodes], range(len(viz_nodes))))
    for (title1, url1) in td_matrix.keys():
        distances[(title1, url1)] = {}
        (min_dist, most_similar) = (1.0, ('', ''))
        for (title2, url2) in td_matrix.keys():
            # Take care not to mutate the original data structures since we're in a loop and need the originals multiple times
            terms1 = td_matrix[(title1, url1)].copy()
            terms2 = td_matrix[(title2, url2)].copy()
            # Fill in "gaps" in each map so vectors of the same length can be computed
            for term1 in terms1:
                if term1 not in terms2:
                    terms2[term1] = 0

            for term2 in terms2:
                if term2 not in terms1:
                    terms1[term2] = 0
            # Create vectors from term maps
            v1 = [score for (term, score) in sorted(terms1.items())]
            v2 = [score for (term, score) in sorted(terms2.items())]
            # Compute similarity amongst documents
            distances[(title1, url1)][(title2, url2)] = \
                nltk.cluster.util.cosine_distance(v1, v2)
            if url1 == url2:
                # print distances[(title1, url1)][(title2, url2)]
                continue
            if distances[(title1, url1)][(title2, url2)] < min_dist:
                (min_dist, most_similar) = (distances[(title1, url1)][(title2,
                                                                       url2)], (title2, url2))
        viz_links.append({'source': idx[title1], 'target': idx[most_similar[0]], 'score': 1 - min_dist})

    f = open('visualization/matrix.json', 'w')
    f.write(json.dumps({'nodes': viz_nodes, 'links': viz_links}, indent=1))
    f.close()

    # Display the visualization below with an inline frame
    display(IFrame('visualization/matrix.html', '100%', '600px'))


def calculate_collocations(fname):
    data = json.loads(open(fname).read())
    N = 25  # Number of collocations to find

    all_tokens = [token for activity in data for token in activity['object']['content'].lower().split()]
    finder = nltk.BigramCollocationFinder.from_words(all_tokens)
    finder.apply_freq_filter(2)
    finder.apply_word_filter(lambda w: w in nltk.corpus.stopwords.words('english'))
    scorer = nltk.metrics.BigramAssocMeasures.jaccard
    collocations = finder.nbest(scorer, N)

    for collocation in collocations:
        c = ' '.join(collocation)
        print c
