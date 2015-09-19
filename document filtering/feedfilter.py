# Example from Programming Collective Intelligence, Chapter 6

import re
import feedparser   # pip install feedparser
import docclass

# Takes a filename of URL of a blog feed and classifies the entries
def read(feed, classifier):
    # Get feed entries and loop over them
    f = feedparser.parse(feed)
    for entry in f['entries']:
        print
        print '-----'
        # Print the contents of the entry
        print 'Title:     ' + entry['title'].encode('utf-8')
        print 'Publisher: ' + entry['publisher'].encode('utf-8')
        print
        print entry['summary'].encode('utf-8')
        # Combine all the text to create one item for the classifier
        fulltext = '%s\n%s\n%s' % (entry['title'], entry['publisher'], entry['summary'])
        # Print the best guess at the current category
        print 'Guess: ' + str(classifier.classify(fulltext))
        # Ask the user to specify the correct category and train on that
        cl = raw_input('Enter category: ')
        classifier.train(fulltext, cl.strip())


def entryfeatures(entry):
    splitter = re.compile('\\W*')
    f = {}
    titlewords = [s.lower() for s in splitter.split(entry['title']) if len(s) > 2 and len(s) < 20]
    for w in titlewords: f['Title:' + w] = 1
    summarywords = [s.lower() for s in splitter.split(entry['summary']) if len(s) > 2 and len(s) < 20]
    # Count uppercase words
    uc = 0
    for i in range(len(summarywords)):
        w = summarywords[i]
        f[w] = 1
        if w.isupper(): uc += 1
        # Get word pairs in summary as features
        if i < len(summarywords) - 1:
            twowords = ' '.join(summarywords[i:i + 1])
            f[twowords] = 1

    # Keep creator and publisher whole
    f['Publisher:' + entry['publisher']] = 1
    # UPPERCASE is a virtual word flagging too much shouting
    if float(uc) / len(summarywords) > 0.3: f['UPPERCASE'] = 1
    return f


def main():
    cl = docclass.fisherclassifier(docclass.getwords)
    read('python_search.xml',cl)
    # Calculate probabilities
    print(cl.cprob('python','prog'))
    print(cl.cprob('python','snake'))
    print(cl.cprob('python','monty'))
    print(cl.cprob('eric','monty'))
    print(cl.fprob('eric','monty'))


if __name__ == "__main__": main()