# Example from Programming Collective Intelligence, Chapter 10

import feedparser   # pip install feedparser
import re

def stripHTML(h):
    p = ''
    s = 0
    for c in h:
        if c == '<':
            s = 1
        elif c == '>':
            s = 0
            p += ' '
        elif s == 0:
            p += c
    return p


def separatewords(text):
    splitter = re.compile('\\W*')
    return [s.lower() for s in splitter.split(text) if len(s) > 3]


def getarticlewords(feedlist):
    allwords = {}
    articlewords = []
    articletitles = []
    ec = 0
    # Loop over every feed
    for feed in feedlist:
        f = feedparser.parse(feed)

        # Loop over every article
        print 'Parsing feed %s, # of entries: %d' % (feed, len(f.entries))
        for e in f.entries:
            # Ignore identical articles
            if e.title in articletitles: continue

            # Extract the words
            txt = e.title.encode('utf8') + stripHTML(e.description.encode('utf8') if e.has_key('description') else '')
            words = separatewords(txt)
            articlewords.append({})
            articletitles.append(e.title)

            # Increase the counts for this word in allwords and in articlewords
            for word in words:
                allwords.setdefault(word, 0)
                allwords[word] += 1
                articlewords[ec].setdefault(word, 0)
                articlewords[ec][word] += 1
            ec += 1
    return allwords, articlewords, articletitles


def makematrix(allw, articlew):
    wordvec = []

    # Only take words that are common but not too common
    for w, c in allw.items():
        if c > 3 and c < len(articlew) * 0.6:
            wordvec.append(w)

            # Create the word matrix
    l1 = [[(word in f and f[word] or 0) for word in wordvec] for f in articlew]
    return l1, wordvec


from numpy import *


def showfeatures(w, h, titles, wordvec, out='features.txt'):
    outfile = file(out, 'w')
    pc, wc = shape(h)
    toppatterns = [[] for i in range(len(titles))]
    patternnames = []

    # Loop over all the features
    for i in range(pc):
        slist = []
        # Create a list of words and their weights
        for j in range(wc):
            slist.append((h[i, j], wordvec[j]))
        # Reverse sort the word list
        slist.sort()
        slist.reverse()

        # Print the first six elements
        n = [s[1] for s in slist[0:6]]
        outfile.write(str(n) + '\n')
        patternnames.append(n)

        # Create a list of articles for this feature
        flist = []
        for j in range(len(titles)):
            # Add the article with its weight
            flist.append((w[j, i], titles[j]))
            toppatterns[j].append((w[j, i], i, titles[j]))

        # Reverse sort the list
        flist.sort()
        flist.reverse()

        # Show the top 3 articles
        for f in flist[0:3]:
            outfile.write(str(f) + '\n')
        outfile.write('\n')

    outfile.close()
    # Return the pattern names for later use
    return toppatterns, patternnames


def showarticles(titles, toppatterns, patternnames, out='articles.txt'):
    outfile = file(out, 'w')

    # Loop over all the articles
    for j in range(len(titles)):
        outfile.write(titles[j].encode('utf8') + '\n')

        # Get the top features for this article and
        # reverse sort them
        toppatterns[j].sort()
        toppatterns[j].reverse()

        # Print the top three patterns
        for i in range(3):
            try:
                outfile.write(str(toppatterns[j][i][0]) + ' ' +
                              str(patternnames[toppatterns[j][i][1]]) + '\n')
            except IndexError, e:
                pass
        outfile.write('\n')

    outfile.close()

