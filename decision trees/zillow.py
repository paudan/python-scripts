# Example from Programming Collective Intelligence, Chapter 7

import xml.dom.minidom
import urllib2

import treepredict

zwskey = "X1-ZWz1chwxis15aj_9skq6"


def getaddressdata(address, city):
    print "Getting data for %s" % address
    escad = address.replace(' ', '+')
    url = 'http://www.zillow.com/webservice/GetDeepSearchResults.htm?'
    url += 'zws-id=%s&address=%s&citystatezip=%s' % (zwskey, escad, city)
    doc = xml.dom.minidom.parseString(urllib2.urlopen(url).read())
    code = doc.getElementsByTagName('code')[0].firstChild.data
    if code != '0': return None
    if 1:
        try:
            zipcode = doc.getElementsByTagName('zipcode')[0].firstChild.data
            use = doc.getElementsByTagName('useCode')[0].firstChild.data
            year = doc.getElementsByTagName('yearBuilt')[0].firstChild.data
            sqft = doc.getElementsByTagName('finishedSqFt')[0].firstChild.data
            bath = doc.getElementsByTagName('bathrooms')[0].firstChild.data
            bed = doc.getElementsByTagName('bedrooms')[0].firstChild.data
            rooms = doc.getElementsByTagName('totalRooms')[0].firstChild.data
            el = doc.getElementsByTagName('amount')[0].firstChild
            if el is None:
                price = 0.0
            else:
                price = el.data
        except IndexError, e:
            return None
    else:
        return None
    return (zipcode, use, int(year), float(bath), int(bed), int(rooms), int(price))


def getpricelist():
    l1 = []
    for line in file('addresslist.txt'):
        data = getaddressdata(line.strip(), 'Cambridge,MA')
        if data is not None:
            l1.append(data)
    return l1


def main():
    housedata = getpricelist()
    housetree = treepredict.buildtree(housedata, scoref=treepredict.variance)
    treepredict.drawtree(housetree, 'housetree.jpg')


if __name__ == "__main__": main()
