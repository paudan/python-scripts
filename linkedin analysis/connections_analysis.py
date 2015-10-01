# Examples from Mining the Social Web, section 3

import os
import codecs
import csv
import json
import re
import webbrowser
from collections import Counter
from operator import itemgetter
from prettytable import PrettyTable
from geopy import geocoders  # pip install geopy
from linkedin import linkedin  # pip install python-linkedin
from nltk.metrics.distance import jaccard_distance
from cluster import HierarchicalClustering, KMeansClustering  # pip install cluster
from cluster.util import centroid
from urllib2 import HTTPError
from linkedin__kml_utility import createKML
from ConfigParser import ConfigParser

# Set utf-8 encoding as default
import sys

reload(sys)
sys.setdefaultencoding('utf8')

CSV_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "LinkedInDataExport", 'Connections.csv')
config = ConfigParser()
config.read('config.ini')
GEO_APP_KEY = config.get('microsoft', 'bing_geo_key')
TOKEN = config.get('linkedin', 'oauth2_access_token')

g = geocoders.Bing(GEO_APP_KEY)
application = linkedin.LinkedInApplication(token=TOKEN)


# connections = application.get_connections()       # Unsupported by LinkedIn


def company_distribution():
    transforms = [(', Inc.', ''), (', Inc', ''), (', LLC', ''), (', LLP', ''),
                  (' LLC', ''), (' Inc.', ''), (' Inc', '')]

    csvReader = csv.DictReader(codecs.open(CSV_FILE, "rb", "utf-16"), delimiter='\t', quotechar='"')
    csvReader.next()
    contacts = [row for row in csvReader]
    companies = [c['Current Company'].strip() for c in contacts if c['Current Company'].strip() != '']

    for i, _ in enumerate(companies):
        for transform in transforms:
            companies[i] = companies[i].replace(*transform)

    pt = PrettyTable(field_names=['Company', 'Freq'])
    pt.align = 'l'
    c = Counter(companies)
    [pt.add_row([company, freq]) for (company, freq) in sorted(c.items(), key=itemgetter(1), reverse=True) if freq > 1]
    print pt


def job_role_distribution():
    transforms = [
        ('Sr.', 'Senior'),
        ('Sr', 'Senior'),
        ('Jr.', 'Junior'),
        ('Jr', 'Junior'),
        ('CEO', 'Chief Executive Officer'),
        ('COO', 'Chief Operating Officer'),
        ('CTO', 'Chief Technology Officer'),
        ('CFO', 'Chief Finance Officer'),
        ('VP', 'Vice President'),
    ]

    csvReader = csv.DictReader(codecs.open(CSV_FILE, "rb", "utf-16"), delimiter='\t', quotechar='"')
    contacts = [row for row in csvReader]
    titles = []
    for contact in contacts:
        titles.extend([t.strip() for t in contact['Current Position'].split('/')
                       if contact['Current Position'].strip() != ''])

    # Replace common/known abbreviations
    for i, _ in enumerate(titles):
        for transform in transforms:
            titles[i] = titles[i].replace(*transform)

    # Print out a table of titles sorted by frequency
    pt = PrettyTable(field_names=['Title', 'Freq'])
    pt.align = 'l'
    c = Counter(titles)
    [pt.add_row([title, freq])
     for (title, freq) in sorted(c.items(), key=itemgetter(1), reverse=True)
     if freq > 1]
    print pt

    # Print out a table of tokens sorted by frequency
    tokens = []
    for title in titles:
        tokens.extend([t.strip(',').capitalize() for t in title.split()])
    pt = PrettyTable(field_names=['Token', 'Freq'])
    pt.align = 'l'
    c = Counter(tokens)
    [pt.add_row([token, freq]) for (token, freq) in sorted(c.items(), key=itemgetter(1), reverse=True) if
     freq > 1 and len(token) > 2]
    print pt


def connection_locations(connections):
    transforms = [('Greater ', ''), (' Area', '')]
    results = {}
    for c in connections['values']:
        if not c.has_key('location'): continue

        transformed_location = c['location']['name']
        for transform in transforms:
            transformed_location = transformed_location.replace(*transform)
        geo = g.geocode(transformed_location, exactly_one=False)
        if geo == []: continue
        results.update({c['location']['name']: geo})

    print json.dumps(results, indent=1)


"""
Parse US states from Bing results
Most results contain a response that can be parsed by picking out the first two consecutive upper case letters
as a clue for the state
"""


def parse_states(connections):
    pattern = re.compile('.*([A-Z]{2}).*')

    def parseStateFromBingResult(r):
        result = pattern.search(r[0][0])
        if result == None:
            print "Unresolved match:", r
            return "???"
        elif len(result.groups()) == 1:
            print result.groups()
            return result.groups()[0]
        else:
            print "Unresolved match:", result.groups()
            return "???"

    transforms = [('Greater ', ''), (' Area', '')]

    results = {}
    for c in connections['values']:
        if not c.has_key('location'): continue
        if not c['location']['country']['code'] == 'us': continue
        transformed_location = c['location']['name']
        for transform in transforms:
            transformed_location = transformed_location.replace(*transform)
        geo = g.geocode(transformed_location, exactly_one=False)
        if geo == []: continue
        parsed_state = parseStateFromBingResult(geo)
        if parsed_state != "???":
            results.update({c['location']['name']: parsed_state})
    print json.dumps(results, indent=1)


def generate_connections_cartogram(results):
    # Load in a data structure mapping state names to codes (e.g. West Virginia is WV)
    codes = json.loads(open('visualization/states-codes.json').read())
    c = Counter([r[1] for r in results.items()])
    states_freqs = {codes[k]: v for (k, v) in c.items()}

    # Lace in all of the other states and provide a minimum value for each of them
    states_freqs.update({v: 0.5 for v in codes.values() if v not in states_freqs.keys()})

    # Write output to file
    f = open('visualization/states-freqs.json', 'w')
    f.write(json.dumps(states_freqs, indent=1))
    f.close()

    webbrowser.open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "visualization", 'cartogram.html'))


# Tweak this distance threshold and try different distance calculations during experimentation
DISTANCE_THRESHOLD = 0.5
DISTANCE = jaccard_distance
# Adjust sample size as needed to reduce the runtime of the nested loop that invokes the DISTANCE function
SAMPLE_SIZE = 500

transforms = [
    ('Sr.', 'Senior'),
    ('Sr', 'Senior'),
    ('Jr.', 'Junior'),
    ('Jr', 'Junior'),
    ('CEO', 'Chief Executive Officer'),
    ('COO', 'Chief Operating Officer'),
    ('CTO', 'Chief Technology Officer'),
    ('CFO', 'Chief Finance Officer'),
    ('VP', 'Vice President'),
]
separators = ['/', ' and ', '&']


def cluster_contacts_by_title(csv_file):
    csvReader = csv.DictReader(codecs.open(csv_file, "rb", "utf-16"), delimiter='\t', quotechar='"')
    csvReader.next()
    contacts = [row for row in csvReader]

    # Normalize and/or replace known abbreviations and build up a list of common titles.
    all_titles = []
    for i, _ in enumerate(contacts):
        if contacts[i]['Current Position'] == '':
            contacts[i]['Job Titles'] = ['']
            continue
        titles = [contacts[i]['Current Position'].strip()]
        for title in titles:
            for separator in separators:
                if title.find(separator) >= 0:
                    titles.remove(title.strip())
                    titles.extend([title.strip() for title in title.split(separator)
                                   if title.strip() != ''])

        for transform in transforms:
            titles = [title.replace(*transform) for title in titles]
        contacts[i]['Job Titles'] = titles
        all_titles.extend(titles)

    all_titles = list(set(all_titles))

    clusters = {}
    for title1 in all_titles:
        clusters[title1] = []
        for title2 in all_titles:
            if title2 in clusters[title1] or clusters.has_key(title2) and title1 \
                    in clusters[title2]:
                continue
            distance = DISTANCE(set(title1.split()), set(title2.split()))

            if distance < DISTANCE_THRESHOLD:
                clusters[title1].append(title2)

    # Flatten out clusters
    clusters = [clusters[title] for title in clusters if len(clusters[title]) > 1]

    # Round up contacts who are in these clusters and group them together
    clustered_contacts = {}
    for cluster in clusters:
        clustered_contacts[tuple(cluster)] = []
        for contact in contacts:
            for title in contact['Job Titles']:
                if title in cluster:
                    clustered_contacts[tuple(cluster)].append('%s %s'
                                                              % (contact['First Name'], contact['Last Name']))

    return clustered_contacts


"""
Incorporating random sampling to to the procedure above to improve performance of the nested loops
"""


def cluster_contacts_by_title_improved(csv_file):
    csvReader = csv.DictReader(codecs.open(csv_file, "rb", "utf-16"), delimiter='\t', quotechar='"')
    csvReader.next()
    contacts = [row for row in csvReader]

    all_titles = []
    for i, _ in enumerate(contacts):
        if contacts[i]['Job Title'] == '':
            contacts[i]['Job Titles'] = ['']
            continue
        titles = [contacts[i]['Job Title'].strip()]
        for title in titles:
            for separator in separators:
                if title.find(separator) >= 0:
                    titles.remove(title.strip())
                    titles.extend([title.strip() for title in title.split(separator)
                                   if title.strip() != ''])

        for transform in transforms:
            titles = [title.replace(*transform) for title in titles]
        contacts[i]['Job Titles'] = titles
        all_titles.extend(titles)

    all_titles = list(set(all_titles))
    clusters = {}
    for title1 in all_titles:
        clusters[title1] = []
        for sample in xrange(SAMPLE_SIZE):
            title2 = all_titles[random.randint(0, len(all_titles) - 1)]
            if title2 in clusters[title1] or clusters.has_key(title2) and title1 \
                    in clusters[title2]:
                continue
            distance = DISTANCE(set(title1.split()), set(title2.split()))
            if distance < DISTANCE_THRESHOLD:
                clusters[title1].append(title2)

    # Flatten out clusters
    clusters = [clusters[title] for title in clusters if len(clusters[title]) > 1]

    # Round up contacts who are in these clusters and group them together
    clustered_contacts = {}
    for cluster in clusters:
        clustered_contacts[tuple(cluster)] = []
        for contact in contacts:
            for title in contact['Job Titles']:
                if title in cluster:
                    clustered_contacts[tuple(cluster)].append('%s %s'
                                                              % (contact['First Name'], contact['Last Name']))

    return clustered_contacts


def display_clusters():
    clustered_contacts = cluster_contacts_by_title(CSV_FILE)
    display_output(clustered_contacts)

    data = {"label": "name", "temp_items": {}, "items": []}
    for titles in clustered_contacts:
        descriptive_terms = set(titles[0].split())
        for title in titles:
            descriptive_terms.intersection_update(set(title.split()))
        descriptive_terms = ', '.join(descriptive_terms)

        if data['temp_items'].has_key(descriptive_terms):
            data['temp_items'][descriptive_terms].extend([{'name': cc} for cc
                                                          in clustered_contacts[titles]])
        else:
            data['temp_items'][descriptive_terms] = [{'name': cc} for cc
                                                     in clustered_contacts[titles]]

    for descriptive_terms in data['temp_items']:
        data['items'].append({"name": "%s (%s)" % (descriptive_terms,
                                                   len(data['temp_items'][descriptive_terms]),),
                              "children": [i for i in
                                           data['temp_items'][descriptive_terms]]})

    del data['temp_items']

    # Open the template and substitute the data

    TEMPLATE = 'visualization/dojo_tree.html.template'
    OUT = 'visualization/dojo_tree.html'

    t = open(TEMPLATE).read()
    f = open(OUT, 'w')
    f.write(t % json.dumps(data, indent=4))
    f.close()

    webbrowser.open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "visualization", 'dojo_tree.html'))


def hierarchical_clustering_by_title(csv_file):
    csvReader = csv.DictReader(codecs.open(csv_file, "rb", "utf-16"), delimiter='\t', quotechar='"')
    csvReader.next()
    contacts = [row for row in csvReader]

    all_titles = []
    for i, _ in enumerate(contacts):
        if contacts[i]['Current Position'] == '':
            contacts[i]['Job Titles'] = ['']
            continue
        titles = [contacts[i]['Current Position']]
        for title in titles:
            for separator in separators:
                if title.find(separator) >= 0:
                    titles.remove(title)
                    titles.extend([title.strip() for title in title.split(separator)
                                   if title.strip() != ''])

        for transform in transforms:
            titles = [title.replace(*transform) for title in titles]
        contacts[i]['Job Titles'] = titles
        all_titles.extend(titles)

    all_titles = list(set(all_titles))

    # Define a scoring function
    def score(title1, title2):
        return DISTANCE(set(title1.split()), set(title2.split()))

    # Feed the class your data and the scoring function
    hc = HierarchicalClustering(all_titles, score)

    # Cluster the data according to a distance threshold
    clusters = hc.getlevel(DISTANCE_THRESHOLD)

    # Remove singleton clusters
    clusters = [c for c in clusters if len(c) > 1]

    # Round up contacts who are in these clusters and group them together

    clustered_contacts = {}
    for cluster in clusters:
        clustered_contacts[tuple(cluster)] = []
        for contact in contacts:
            for title in contact['Job Titles']:
                if title in cluster:
                    clustered_contacts[tuple(cluster)].append('%s %s'
                                                              % (contact['First Name'], contact['Last Name']))

    return clustered_contacts


def display_output(clustered_contacts):
    for titles in clustered_contacts:
        common_titles_heading = 'Common Titles: ' + ', '.join(titles)

        descriptive_terms = set(titles[0].split())
        for title in titles:
            descriptive_terms.intersection_update(set(title.split()))
        descriptive_terms_heading = 'Descriptive Terms: ' \
                                    + ', '.join(descriptive_terms)
        print descriptive_terms_heading
        print '-' * max(len(descriptive_terms_heading), len(common_titles_heading))
        print '\n'.join(clustered_contacts[titles])
        print


def display_cluster_dendrogram():
    def write_d3_json_output(clustered_contacts):
        json_output = {'name': 'My LinkedIn', 'children': []}
        for titles in clustered_contacts:
            descriptive_terms = set(titles[0].split())
            for title in titles:
                descriptive_terms.intersection_update(set(title.split()))
            json_output['children'].append({'name': ', '.join(descriptive_terms)[:30],
                                            'children': [{'name': c.decode('utf-8', 'replace')} for c in
                                                         clustered_contacts[titles]]})
            OUT_FILE = 'visualization/d3-data.json'
            f = open(OUT_FILE, 'w')
            f.write(json.dumps(json_output, indent=1))
            f.close()

    clustered_contacts = cluster_contacts_by_title(CSV_FILE)
    display_output(clustered_contacts)
    write_d3_json_output(clustered_contacts)
    webbrowser.open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "visualization", 'dendogram.html'))
    webbrowser.open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "visualization", 'node_link_tree.html'))


"""
Generate clusters of LinkedIn connections according to their locations of your connections and produce KML output
for visualization with Google Earth
Unfortunately, this is not supported by LinkedIn anymore
"""
def generate_locations_kml(connections_json):
    K = 3  # The number of clusters
    OUT_FILE = "linkedin_clusters_kmeans.kml"

    connections = json.loads(open(connections_json).read())['values']
    locations = [c['location']['name'] for c in connections if c.has_key('location')]

    # Some basic transforms may be necessary for geocoding services to function properly
    # Here are a couple that seem to help.
    transforms = [('Greater ', ''), (' Area', '')]

    # Step 1 - Tally the frequency of each location
    coords_freqs = {}
    for location in locations:

        if not c.has_key('location'): continue

        # Avoid unnecessary I/O and geo requests by building up a cache
        if coords_freqs.has_key(location):
            coords_freqs[location][1] += 1
            continue
        transformed_location = location

        for transform in transforms:
            transformed_location = transformed_location.replace(*transform)

            # Handle potential I/O errors with a retry pattern...
            while True:
                num_errors = 0
                try:
                    results = g.geocode(transformed_location, exactly_one=False)
                    break
                except HTTPError, e:
                    num_errors += 1
                    if num_errors >= 3:
                        sys.exit()
                    print >> sys.stderr, e
                    print >> sys.stderr, 'Encountered an urllib2 error. Trying again...'

            for result in results:
                # Each result is of the form ("Description", (X,Y))
                coords_freqs[location] = [result[1], 1]
                break  # Disambiguation strategy is "pick first"

    # Step 2 - Build up data structure for converting locations to KML

    # Here, you could optionally segment locations by continent or country
    # so as to avoid potentially finding a mean in the middle of the ocean.
    # The k-means algorithm will expect distinct points for each contact, so
    # build out an expanded list to pass it.

    expanded_coords = []
    for label in coords_freqs:
        # Flip lat/lon for Google Earth
        ((lat, lon), f) = coords_freqs[label]
        expanded_coords.append((label, [(lon, lat)] * f))

    # No need to clutter the map with unnecessary placemarks...

    kml_items = [{'label': label, 'coords': '%s,%s' % coords[0]} for (label,
                                                                      coords) in expanded_coords]

    # It would also be helpful to include names of your contacts on the map

    for item in kml_items:
        item['contacts'] = '\n'.join(['%s %s.' % (c['firstName'], c['lastName'])
                                      for c in connections if c.has_key('location') and
                                      c['location']['name'] == item['label']])

    # Step 3 - Cluster locations and extend the KML data structure with centroids

    cl = KMeansClustering([coords for (label, coords_list) in expanded_coords
                           for coords in coords_list])
    centroids = [{'label': 'CENTROID', 'coords': '%s,%s' % centroid(c)} for c in
                 cl.getclusters(K)]
    kml_items.extend(centroids)

    # Step 4 - Create the final KML output and write it to a file
    kml = createKML(kml_items)
    f = open(OUT_FILE, 'w')
    f.write(kml)
    f.close()
    print 'Data written to ' + OUT_FILE


def main():
    # company_distribution()
    # job_role_distribution()
    # g = geocoders.Bing(GEO_APP_KEY)
    # print g.geocode("Nashville", exactly_one=False)
    display_clusters()
    display_cluster_dendrogram()


if __name__ == "__main__": main()
