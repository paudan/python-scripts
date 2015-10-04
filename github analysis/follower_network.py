# Examples from Mining the Social Web, section 7

import requests
import json
import sys
import os
from operator import itemgetter
from collections import Counter
import webbrowser
from github import Github
import networkx as nx  # pip install networkx
from networkx.readwrite import json_graph
from ConfigParser import ConfigParser

# Set utf-8 encoding as default
reload(sys)
sys.setdefaultencoding('utf8')

config = ConfigParser()
config.read('config.ini')
username = config.get('github', 'username')
password = config.get('github', 'password')
token = config.get('github', 'token')


def create_access_token():
    # Note that credentials will be transmitted over a secure SSL connection
    url = 'https://api.github.com/authorizations'
    note = 'Mining the Social Web, 2nd Ed.'
    post_data = {'scopes': ['repo'], 'note': note}

    response = requests.post(url, auth=(username, password), data=json.dumps(post_data), )

    print "API response:", response.text
    if response.json()['errors']:
        print response.json()['errors'][0]['code']
    else:
        print "Your OAuth token is", response.json()['token']


# An unauthenticated request that doesn't contain an ?access_token=xxx query string
def get_stargazers():
    create_access_token()
    url = "https://api.github.com/repos/ptwobrussell/Mining-the-Social-Web/stargazers"
    response = requests.get(url)
    print json.dumps(response.json()[0], indent=1)
    print
    for (k, v) in response.headers.items():
        print k, "=>", v


def create_stargazers_graph():
    USER = 'ptwobrussell'
    REPO = 'Mining-the-Social-Web'

    client = Github(token, per_page=100)
    user = client.get_user(USER)
    repo = user.get_repo(REPO)

    stargazers = [s for s in repo.get_stargazers()]
    print "Number of stargazers", len(stargazers)

    g = nx.DiGraph()
    g.add_node(repo.name + '(repo)', type='repo', lang=repo.language, owner=user.login)

    for sg in stargazers:
        g.add_node(sg.login + '(user)', type='user')
        g.add_edge(sg.login + '(user)', repo.name + '(repo)', type='gazes')

    print nx.info(g)
    print
    print g.node['Mining-the-Social-Web(repo)']
    print g.node['ptwobrussell(user)']
    print
    print g['ptwobrussell(user)']['Mining-the-Social-Web(repo)']
    # The next line would throw a KeyError since no such edge exists:
    # print g['Mining-the-Social-Web(repo)']['ptwobrussell(user)']
    print
    print g['ptwobrussell(user)']
    print g['Mining-the-Social-Web(repo)']
    print
    print g.in_edges(['ptwobrussell(user)'])
    print g.out_edges(['ptwobrussell(user)'])
    print
    print g.in_edges(['Mining-the-Social-Web(repo)'])
    print g.out_edges(['Mining-the-Social-Web(repo)'])

    # The classic Krackhardt kite graph
    kkg = nx.generators.small.krackhardt_kite_graph()
    print "Degree Centrality"
    print sorted(nx.degree_centrality(kkg).items(), key=itemgetter(1), reverse=True)
    print
    print "Betweenness Centrality"
    print sorted(nx.betweenness_centrality(kkg).items(), key=itemgetter(1), reverse=True)
    print
    print "Closeness Centrality"
    print sorted(nx.closeness_centrality(kkg).items(), key=itemgetter(1), reverse=True)

    for i, sg in enumerate(stargazers):
        # Add "follows" edges between stargazers in the graph if any relationships exist
        try:
            for follower in sg.get_followers():
                if follower.login + '(user)' in g:
                    g.add_edge(follower.login + '(user)', sg.login + '(user)', type='follows')
        except Exception, e:  # ssl.SSLError
            print >> sys.stderr, "Encountered an error fetching followers for", sg.login, "Skipping."
            print >> sys.stderr, e
        print "Processed", i + 1, " stargazers. Num nodes/edges in graph", \
            g.number_of_nodes(), "/", g.number_of_edges()
        print "Rate limit remaining", client.rate_limiting

    # Let's see how many social edges we added since last time.
    print nx.info(g)
    print
    # The number of "follows" edges is the difference
    print len([e for e in g.edges_iter(data=True) if e[2]['type'] == 'follows'])
    print
    # The repository owner is possibly one of the more popular users in this graph.
    print len([e for e in g.edges_iter(data=True) if e[2]['type'] == 'follows' and e[1] == 'ptwobrussell(user)'])
    print
    # Let's examine the number of adjacent edges to each node
    print sorted([n for n in g.degree_iter()], key=itemgetter(1), reverse=True)[:10]
    print

    # A user who follows many but is not followed back by many.
    print len(g.out_edges('hcilab(user)'))
    print len(g.in_edges('hcilab(user)'))
    print

    # A user who is followed by many but does not follow back.
    print len(g.out_edges('ptwobrussell(user)'))
    print len(g.in_edges('ptwobrussell(user)'))
    print

    c = Counter([e[1] for e in g.edges_iter(data=True) if e[2]['type'] == 'follows'])
    popular_users = [(u, f) for (u, f) in c.most_common() if f > 1]
    print "Number of popular users", len(popular_users)
    print "Top 10 popular users:", popular_users[:10]

    # Save your work by serializing out (pickling) the graph
    nx.write_gpickle(g, "data/github.gpickle.1")
    # analyse_centrality_measures(g)
    #
    # # Let's add each stargazer's additional starred repos and add edges to find additional interests.
    # MAX_REPOS = 500
    # for i, sg in enumerate(stargazers):
    #     print sg.login
    #     try:
    #         for starred in sg.get_starred()[:MAX_REPOS]:  # Slice to avoid supernodes
    #             g.add_node(starred.name + '(repo)', type='repo', lang=starred.language, \
    #                        owner=starred.owner.login)
    #             g.add_edge(sg.login + '(user)', starred.name + '(repo)', type='gazes')
    #     except Exception, e:  # ssl.SSLError:
    #         print "Encountered an error fetching starred repos for", sg.login, "Skipping."
    #     print "Processed", i + 1, "stargazers' starred repos"
    #     print "Num nodes/edges in graph", g.number_of_nodes(), "/", g.number_of_edges()
    #     print "Rate limit", client.rate_limiting
    #
    # # Save your work by serializing out another snapshot of the graph
    # nx.write_gpickle(g, "data/github.gpickle.2")
    # analyse_repositories(g)
    #
    # # Update graph to include nodes for programming languages
    # # Iterate over all of the repos, and add edges for programming languages for each person in the graph.
    # # We'll also add edges back to repos so that we have a good point to "pivot" upon.
    # repos = [n for n in g.nodes_iter() if g.node[n]['type'] == 'repo']
    # for repo in repos:
    #     lang = (g.node[repo]['lang'] or "") + "(lang)"
    #     stargazers = [u for (u, r, d) in g.in_edges_iter(repo, data=True) if d['type'] == 'gazes']
    #     for sg in stargazers:
    #         g.add_node(lang, type='lang')
    #         g.add_edge(sg, lang, type='programs')
    #         g.add_edge(lang, repo, type='implements')
    #
    # nx.write_gpickle(g, "data/github.gpickle.3")
    # analyse_programming_languages(g)
    #
    # print "Stats on the full graph"
    # print nx.info(g)
    # print
    #
    # # Create a subgraph from a collection of nodes. In this case, the collection is all of the users in the original interest graph
    # mtsw_users = [n for n in g if g.node[n]['type'] == 'user']
    # h = g.subgraph(mtsw_users)
    #
    # print "Stats on the extracted subgraph"
    # print nx.info(h)
    #
    # # Visualize the social network of all people from the original interest graph.
    # d = json_graph.node_link_data(h)
    # json.dump(d, open('visualization/force.json', 'w'))
    #
    # viz_file = 'visualization/force.html'
    # webbrowser.open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "visualization", 'force.html'))


def load_graph_after_create(nx):
    # Graph restoring from the pickle
    g = nx.read_gpickle("data/github.gpickle.1")
    analyse_centrality_measures(g)


def analyse_centrality_measures(g):
    print "Centrality measures"
    # Create a copy of the graph so that we can iteratively mutate the copy as needed for experimentation
    h = g.copy()

    # Remove the seed of the interest graph, which is a supernode, in order to get a better idea of the network dynamics
    h.remove_node('Mining-the-Social-Web(repo)')

    # XXX: Remove any other nodes that appear to be supernodes. Filter any other nodes that you can by threshold
    # criteria or heuristics from inspection.
    dc = sorted(nx.degree_centrality(h).items(), key=itemgetter(1), reverse=True)
    print "Degree Centrality"
    print dc[:10]
    print

    bc = sorted(nx.betweenness_centrality(h).items(), key=itemgetter(1), reverse=True)
    print "Betweenness Centrality"
    print bc[:10]
    print

    print "Closeness Centrality"
    cc = sorted(nx.closeness_centrality(h).items(), key=itemgetter(1), reverse=True)
    print cc[:10]


def load_graph_with_repos(nx):
    # Graph restoring from the pickle
    g = nx.read_gpickle("data/github.gpickle.2")
    analyse_repositories(g)


def analyse_repositories(g):
    print nx.info(g)
    print
    # Get a list of repositories from the graph.
    repos = [n for n in g.nodes_iter() if g.node[n]['type'] == 'repo']
    # Most popular repos
    print "Popular repositories"
    print sorted([(n, d) for (n, d) in g.in_degree_iter()
                  if g.node[n]['type'] == 'repo'], key=itemgetter(1), reverse=True)[:10]
    print

    # Projects gazed at by a user
    print "Respositories that ptwobrussell has bookmarked"
    print [(n, g.node[n]['lang']) for n in g['ptwobrussell(user)']
           if g['ptwobrussell(user)'][n]['type'] == 'gazes']
    print

    # Programming languages for each user
    print "Programming languages ptwobrussell is interested in"
    print list(set([g.node[n]['lang'] for n in g['ptwobrussell(user)']
                    if g['ptwobrussell(user)'][n]['type'] == 'gazes']))
    print

    # Find supernodes in the graph by approximating with a high number of outgoing edges
    print "Supernode candidates"
    print sorted([(n, len(g.out_edges(n))) for n in g.nodes_iter()
                  if g.node[n]['type'] == 'user' and len(g.out_edges(n)) > 500], key=itemgetter(1), reverse=True)


def load_graph_with_languages(nx):
    # Graph restoring from the pickle
    g = nx.read_gpickle("data/github.gpickle.2")
    analyse_repositories(g)


def analyse_programming_languages(g):
    # Some queries for the graph
    print nx.info(g)
    print

    # What languages exist in the graph?
    print [n for n in g.nodes_iter() if g.node[n]['type'] == 'lang']
    print

    # What languages do users program with?
    print [n for n in g['ptwobrussell(user)'] if g['ptwobrussell(user)'][n]['type'] == 'programs']

    # What is the most popular programming language?
    print "Most popular languages"
    print sorted([(n, g.in_degree(n)) for n in g.nodes_iter()
                  if g.node[n]['type'] == 'lang'], key=itemgetter(1), reverse=True)[:10]
    print

    # How many users program in a particular language?
    python_programmers = [u for (u, l) in g.in_edges_iter('Python(lang)') if g.node[u]['type'] == 'user']
    print "Number of Python programmers:", len(python_programmers)
    print

    javascript_programmers = [u for (u, l) in g.in_edges_iter('JavaScript(lang)')
                              if g.node[u]['type'] == 'user']
    print "Number of JavaScript programmers:", len(javascript_programmers)
    print

    # What users program in both Python and JavaScript?
    print "Number of programmers who use JavaScript and Python"
    print len(set(python_programmers).intersection(set(javascript_programmers)))

    # Programmers who use JavaScript but not Python
    print "Number of programmers who use JavaScript but not Python"
    print len(set(javascript_programmers).difference(set(python_programmers)))


create_stargazers_graph()
