# Examples from Mining the Social Web, section 2

import facebook
import json
from ConfigParser import ConfigParser

config = ConfigParser()
config.read('fbconfig.ini')
token = config.get('fbconfig-analytics', 'access_token')


# A helper function to pretty-print Python objects as JSON
def pp(o):
    print json.dumps(o, indent=1)


# Create a connection to the Graph API with your access token
g = facebook.GraphAPI(token)
print '---------------'
print 'Me'
print '---------------'
pp(g.get_object('me'))
print
print '---------------'
print 'My Friends'
print '---------------'
pp(g.get_connections('me', 'friends'))
print
print '---------------'
print 'Social Web'
print '---------------'
pp(g.request("search", {'q' : 'social web', 'type' : 'page'}))
# Get an instance of Mining the Social Web
# Using the page name also works if you know it.
print
print '---------------'
print 'Mining the Social Web page'
print '---------------'
mtsw_id = '146803958708175'
pp(g.get_object(mtsw_id))
# Querying the Graph API for Open Graph objects by their URLs
pp(g.get_object('http://shop.oreilly.com/product/0636920030195.do'))
# PCI catalog link
print '---------------'
print 'Programming Collective Intelligence'
print '---------------'
pp(g.get_object('http://shop.oreilly.com/product/9780596529321.do'))

# Comparing likes between Coke and Pepsi fan pages
print "Find Pepsi and Coke in search results"
pp(g.request('search', {'q': 'pepsi', 'type': 'page', 'limit': 5}))
pp(g.request('search', {'q': 'coke', 'type': 'page', 'limit': 5}))
# Use the ids to query for likes
pepsi_id = '56381779049'  # Could also use 'PepsiUS'
coke_id = '40796308305'  # Could also use 'CocaCola'
# Querying a page for its feed
pp(g.get_connections(pepsi_id, 'feed'))
# pp(g.get_connections(pepsi_id, 'links'))  # Does not work with v2.4
pp(g.get_connections(coke_id, 'feed'))
# pp(g.get_connections(coke_id, 'links'))

# Analyze all likes from friendships for frequency (apparently, does not work since 2015 April)

from prettytable import PrettyTable # pip install prettytable
from collections import Counter

friends = g.get_connections("me", "friends")['data']
likes = {friend['name'] : g.get_connections(friend['id'], "likes")['data'] for friend in friends }
friends_likes = Counter([like['name'] for friend in likes for like in likes[friend] if like.get('name')])
pt = PrettyTable(field_names=['Name', 'Freq'])
pt.align['Name'], pt.align['Freq'] = 'l', 'r'
[pt.add_row(fl) for fl in friends_likes.most_common(10)]
print 'Top 10 likes amongst friends'
print pt

# Analyze all like categories by frequency
friends_likes_categories = Counter([like['category'] for friend in likes for like in likes[friend]])
pt = PrettyTable(field_names=['Category', 'Freq'])
pt.align['Category'], pt.align['Freq'] = 'l', 'r'
[pt.add_row(flc) for flc in friends_likes_categories.most_common(10)]
print "Top 10 like categories for friends"
print pt

# Build a frequency distribution of number of likes by
# friend with a dictionary comprehension and sort it in descending order
from operator import itemgetter
num_likes_by_friend = { friend : len(likes[friend]) for friend in likes }
pt = PrettyTable(field_names=['Friend', 'Num Likes'])
pt.align['Friend'], pt.align['Num Likes'] = 'l', 'r'
[ pt.add_row(nlbf) for nlbf in sorted(num_likes_by_friend.items(), key=itemgetter(1), reverse=True)]
print "Number of likes per friend"
print pt

# Which of your likes are in common with which friends?
my_likes = [like['name'] for like in g.get_connections("me", "likes")['data']]
pt = PrettyTable(field_names=["Name"])
pt.align = 'l'
[pt.add_row((ml,)) for ml in my_likes]
print "My likes"
print pt
# Use the set intersection as represented by the ampersand operator to find common likes.
common_likes = list(set(my_likes) & set(friends_likes))
pt = PrettyTable(field_names=["Name"])
pt.align = 'l'
[pt.add_row((cl,)) for cl in common_likes]
print
print "My common likes with friends"
print pt

# Which of your friends like things that you like?
similar_friends = [ (friend, friend_like['name'])
                    for friend, friend_likes in likes.items()
                    for friend_like in friend_likes
                    if friend_like.get('name') in common_likes ]
# Filter out any possible duplicates that could occur
ranked_friends = Counter([ friend for (friend, like) in list(set(similar_friends))])
pt = PrettyTable(field_names=["Friend", "Common Likes"])
pt.align["Friend"], pt.align["Common Likes"] = 'l', 'r'
[pt.add_row(rf) for rf in sorted(ranked_friends.items(), key=itemgetter(1), reverse=True)]
print "My similar friends (ranked)"
print pt

# A quick histogram that shows how many friends
if ranked_friends.values() :
    from matplotlib.pyplot import *
    from numpy import array, arange
    hist(ranked_friends.values())
    xlabel('Bins (number of friends with shared likes)')
    ylabel('Number of shared likes in each bin')
    figure() # Display the previous plot
    hist(ranked_friends.values(), bins=arange(1,max(ranked_friends.values()),1))
    xlabel('Bins (number of friends with shared likes)')
    ylabel('Number of shared likes in each bin')
    figure() # Display the working plot