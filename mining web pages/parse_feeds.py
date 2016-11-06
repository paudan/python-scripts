import shutil
import sys
import json
import nltk
import io
import numpy
import os
from os import path

sys.path.insert(0, '../google analysis')
from google_search import cleanHtml

# sys.stdout = codecs.getwriter('utf8')(sys.stdout)
FEED_URL = 'http://feeds.feedburner.com/oreilly/radar/atom'

N = 100  # Number of words to consider
CLUSTER_THRESHOLD = 5  # Distance between words to consider
TOP_SENTENCES = 5  # Number of sentences to return for a "top n" summary

nltk.download('stopwords')
stop_words = nltk.corpus.stopwords.words('english') + [
    '.',
    ',',
    '--',
    '\'s',
    '?',
    ')',
    '(',
    ':',
    '\'',
    '\'re',
    '"',
    '-',
    '}',
    '{',
    u'\x97'
]

# Approach taken from "The Automatic Creation of Literature Abstracts" by H.P. Luhn
def _score_sentences(sentences, important_words):
    scores = []
    sentence_idx = -1

    for s in [nltk.tokenize.word_tokenize(s) for s in sentences]:

        sentence_idx += 1
        word_idx = []

        # For each word in the word list...
        for w in important_words:
            try:
                # Compute an index for where any important words occur in the sentence.

                word_idx.append(s.index(w))
            except ValueError, e:  # w not in this particular sentence
                pass

        word_idx.sort()

        # It is possible that some sentences may not contain any important words at all.
        if len(word_idx) == 0: continue

        # Using the word index, compute clusters by using a max distance threshold
        # for any two consecutive words.

        clusters = []
        cluster = [word_idx[0]]
        i = 1
        while i < len(word_idx):
            if word_idx[i] - word_idx[i - 1] < CLUSTER_THRESHOLD:
                cluster.append(word_idx[i])
            else:
                clusters.append(cluster[:])
                cluster = [word_idx[i]]
            i += 1
        clusters.append(cluster)

        # Score each cluster. The max score for any given cluster is the score
        # for the sentence.

        max_cluster_score = 0
        for c in clusters:
            significant_words_in_cluster = len(c)
            total_words_in_cluster = c[-1] - c[0] + 1
            score = 1.0 * significant_words_in_cluster \
                    * significant_words_in_cluster / total_words_in_cluster

            if score > max_cluster_score:
                max_cluster_score = score

        scores.append((sentence_idx, score))

    return scores


def summarize(txt):
    sentences = [s for s in nltk.tokenize.sent_tokenize(txt)]
    normalized_sentences = [s.lower() for s in sentences]

    words = [w.lower() for sentence in normalized_sentences for w in
             nltk.tokenize.word_tokenize(sentence)]

    fdist = nltk.FreqDist(words)

    top_n_words = [w[0] for w in fdist.items()
                   if w[0] not in nltk.corpus.stopwords.words('english')][:N]

    scored_sentences = _score_sentences(normalized_sentences, top_n_words)

    # Summarization Approach 1:
    # Filter out nonsignificant sentences by using the average score plus a
    # fraction of the std dev as a filter

    avg = numpy.mean([s[1] for s in scored_sentences])
    std = numpy.std([s[1] for s in scored_sentences])
    mean_scored = [(sent_idx, score) for (sent_idx, score) in scored_sentences
                   if score > avg + 0.5 * std]

    # Summarization Approach 2:
    # Another approach would be to return only the top N ranked sentences

    top_n_scored = sorted(scored_sentences, key=lambda s: s[1])[-TOP_SENTENCES:]
    top_n_scored = sorted(top_n_scored, key=lambda s: s[0])

    # Decorate the post object with summaries
    return dict(top_n_summary=[sentences[idx] for (idx, score) in top_n_scored],
                mean_scored_summary=[sentences[idx] for (idx, score) in mean_scored])


def visualize_summarization_results(fname):
    from IPython.display import IFrame
    from IPython.core.display import display

    HTML_TEMPLATE = """<html>
    <head>
        <title>%s</title>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
    </head>
    <body>%s</body>
</html>"""

    blog_data = json.loads(open(fname).read())
    dirname = path.join(path.dirname(path.realpath(__file__)), 'summarization')
    if path.isdir(dirname):
        shutil.rmtree(dirname)
    os.mkdir(dirname)
    for post in blog_data:
        post.update(summarize(post['content']))
        for summary_type in ['top_n_summary', 'mean_scored_summary']:
            post[summary_type + '_marked_up'] = '<p>%s</p>' % (post['content'],)
            for s in post[summary_type]:
                post[summary_type + '_marked_up'] = \
                    post[summary_type + '_marked_up'].replace(s, '<strong>%s</strong>' % (s,))
            filename = path.join(dirname, post['title'].replace("?", "") + '.summary.' + summary_type + '.html')
            f = open(filename, 'w')
            html = HTML_TEMPLATE % (post['title'] + \
                                    ' Summary', post[summary_type + '_marked_up'],)
            f.write(html.encode('utf-8'))
            f.close()

            print "Data written to", f.name

    # Display any of these files with an inline frame. This displays the
    # last file processed by using the last value of f.name...
    print "Displaying %s:" % f.name
    display(IFrame('file:///%s' % f.name, '100%', '300px'))


def extract_entities(fname):
    blog_data = json.loads(open(fname).read())
    for post in blog_data:

        sentences = nltk.tokenize.sent_tokenize(post['content'])
        tokens = [nltk.tokenize.word_tokenize(s) for s in sentences]
        pos_tagged_tokens = [nltk.pos_tag(t) for t in tokens]

        # Flatten the list since we're not using sentence structure and sentences are
        # guaranteed to be separated by a special POS tuple such as ('.', '.')
        pos_tagged_tokens = [token for sent in pos_tagged_tokens for token in sent]
        all_entity_chunks = []
        previous_pos = None
        current_entity_chunk = []
        for (token, pos) in pos_tagged_tokens:

            if pos == previous_pos and pos.startswith('NN'):
                current_entity_chunk.append(token)
            elif pos.startswith('NN'):
                if current_entity_chunk != []:
                    # Note that current_entity_chunk could be a duplicate when appended,
                    # so frequency analysis again becomes a consideration
                    all_entity_chunks.append((' '.join(current_entity_chunk), pos))
                current_entity_chunk = [token]
            previous_pos = pos

        # Store the chunks as an index for the document and account for frequency
        post['entities'] = {}
        for c in all_entity_chunks:
            post['entities'][c] = post['entities'].get(c, 0) + 1

        print post['title']
        print '-' * len(post['title'])
        proper_nouns = []
        for (entity, pos) in post['entities']:
            if entity.istitle():
                print '\t%s (%s)' % (entity, post['entities'][(entity, pos)])
        print


def extract_interactions(txt):
    sentences = nltk.tokenize.sent_tokenize(txt)
    tokens = [nltk.tokenize.word_tokenize(s) for s in sentences]
    pos_tagged_tokens = [nltk.pos_tag(t) for t in tokens]

    entity_interactions = []
    for sentence in pos_tagged_tokens:

        all_entity_chunks = []
        previous_pos = None
        current_entity_chunk = []

        for (token, pos) in sentence:
            if pos == previous_pos and pos.startswith('NN'):
                current_entity_chunk.append(token)
            elif pos.startswith('NN'):
                if current_entity_chunk != []:
                    all_entity_chunks.append((' '.join(current_entity_chunk), pos))
                current_entity_chunk = [token]
            previous_pos = pos

        if len(all_entity_chunks) > 1:
            entity_interactions.append(all_entity_chunks)
        else:
            entity_interactions.append([])

    assert len(entity_interactions) == len(sentences)
    return dict(entity_interactions=entity_interactions, sentences=sentences)


def visualize_interactions(fname):
    from IPython.display import IFrame
    from IPython.core.display import display

    HTML_TEMPLATE = """<html>
    <head>
        <title>%s</title>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
    </head>
    <body>%s</body>
</html>"""

    blog_data = json.loads(open(fname).read())
    dirname = path.join(path.dirname(path.realpath(__file__)), 'interactions')
    if path.isdir(dirname):
        shutil.rmtree(dirname)
    os.mkdir(dirname)
    for post in blog_data:
        post.update(extract_interactions(post['content']))

        # Display output as markup with entities presented in bold text
        post['markup'] = []
        for sentence_idx in range(len(post['sentences'])):

            s = post['sentences'][sentence_idx]
            for (term, _) in post['entity_interactions'][sentence_idx]:
                s = s.replace(term, '<strong>%s</strong>' % (term, ))

            post['markup'] += [s]

        filename = post['title'].replace("?", "") + '.entity_interactions.html'
        f = open(os.path.join(dirname, filename), 'w')
        html = HTML_TEMPLATE % (post['title'] + ' Interactions', ' '.join(post['markup']),)
        f.write(html.encode('utf-8'))
        f.close()

        print "Data written to", f.name
        print "Displaying %s:" % f.name
        display(IFrame('file:///%s' % f.name, '100%', '300px'))


def discover_interactions():
    fname = 'feed.json'
    blog_data = json.loads(open(fname).read())
    f = io.open('interactions.txt', 'w', encoding='utf8')
    for post in blog_data:
        post.update(extract_interactions(post['content']))
        f.write(post['title'] + '\n')
        f.write(u'-' * len(post['title']) + '\n\n')
        for interactions in post['entity_interactions']:
            f.write(u'; '.join([i[0] for i in interactions]) + '\n')
    f.close()
    visualize_interactions(fname)


def create_summarizations():
    fname = 'feed.json'
    blog_data = json.loads(open(fname).read())
    f = io.open('summarizations.txt', 'w', encoding='utf8')
    for post in blog_data:
        post.update(summarize(post['content']))
        f.write(post['title'] + '\n')
        f.write(u'=' * len(post['title']) + '\n\n')
        f.write(u'Top N Summary\n')
        f.write(u'-------------\n')
        f.write(u' '.join(post['top_n_summary']) + '\n')
        f.write(u'-------------------\n')
        f.write(u'Mean Scored Summary\n')
        f.write(u'-------------------\n')
        f.write(u' '.join(post['mean_scored_summary']) + '\n\n')
    f.close()
    visualize_summarization_results(fname)


# create_summarizations()
# discover_interactions()