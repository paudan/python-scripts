# Constructing a graph of mutual friendships
# Example from Mining the Social Web, section 2

import networkx as nx  # pip install networkx
import requests  # pip install requests
import json
import facebook
from ConfigParser import ConfigParser

config = ConfigParser()
config.read('fbconfig.ini')
token = config.get('fbconfig-analytics', 'access_token')

g = facebook.GraphAPI(token)
friends = [(friend['id'], friend['name'],)
           for friend in g.get_connections('me', 'friends')['data']]
url = 'https://graph.facebook.com/me/mutualfriends/%s?access_token=%s'
mutual_friends = {}
# This loop spawns a separate request for each iteration, so
# it may take a while. Optimization with a thread pool or similar
# technique would be possible.
for friend_id, friend_name in friends:
    r = requests.get(url % (friend_id, token))
    response_data = json.loads(r.content)['data']
    mutual_friends[friend_name] = [data['name'] for data in response_data]
nxg = nx.Graph()
[nxg.add_edge('me', mf) for mf in mutual_friends]
[nxg.add_edge(f1, f2)
 for f1 in mutual_friends
 for f2 in mutual_friends[f1]]
print nxg

# Finding cliques is a hard problem, so this could take a while for large graphs
cliques = [c for c in nx.find_cliques(nxg)]
num_cliques = len(cliques)
clique_sizes = [len(c) for c in cliques]
if clique_sizes:
    max_clique_size = max(clique_sizes)
    avg_clique_size = sum(clique_sizes) / num_cliques
    max_cliques = [c for c in cliques if len(c) == max_clique_size]
    num_max_cliques = len(max_cliques)
    max_clique_sets = [set(c) for c in max_cliques]
    friends_in_all_max_cliques = list(reduce(lambda x, y: x.intersection(y), max_clique_sets))
    print 'Num cliques:', num_cliques
    print 'Avg clique size:', avg_clique_size
    print 'Max clique size:', max_clique_size
    print 'Num max cliques:', num_max_cliques
    print
    print 'Friends in all max cliques:'
    print json.dumps(friends_in_all_max_cliques, indent=1)
    print
    print 'Max cliques:'
    print json.dumps(max_cliques, indent=1)
