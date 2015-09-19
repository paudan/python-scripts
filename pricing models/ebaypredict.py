# Example from Programming Collective Intelligence, Chapter 8

import httplib
from xml.dom.minidom import parse, parseString, Node
import numpredict
from ebay.utils import set_config_file, get_config_store      # pip install python-ebay
from ebay.finding import findItemsByKeywords

# Setting eBay configuration values, as necessary by python-ebay module, and reading them from the config file
set_config_file("ebay.apikey")
configStore = get_config_store()
devKey = configStore.get('keys', 'dev_name')
appKey = configStore.get('keys', 'app_name')
certKey = configStore.get('keys', 'cert_name')
userToken = configStore.get('auth', 'token')


def getHeaders(apicall, siteID="0", compatibilityLevel="433"):
    headers = {"X-EBAY-API-COMPATIBILITY-LEVEL": compatibilityLevel,
               "X-EBAY-API-DEV-NAME": devKey,
               "X-EBAY-API-APPr-NAME": appKey,
               "X-EBAY-API-CERT-NAME": certKey,
               "X-EBAY-API-CALL-NAME": apicall,
               "X-EBAY-API-SITEID": siteID,
               "Content-Type": "text/xml"}
    return headers


def sendRequest(apicall, xmlparameters):
    connection = httplib.HTTPSConnection('api.ebay.com')
    connection.request("POST", '/ws/api.dll', xmlparameters, getHeaders(apicall))
    response = connection.getresponse()
    if response.status != 200:
        print "Error sending request:" + response.reason
    else:
        data = response.read()
        connection.close()
    return data

def getSingleValue(node, tag):
    nl = node.getElementsByTagName(tag)
    if len(nl) > 0:
        tagNode = nl[0]
        if tagNode.hasChildNodes():
            return tagNode.firstChild.nodeValue
    return '-1'


def doSearch(query, pageNum=1):
    data = findItemsByKeywords(query, paginationInput = {"entriesPerPage": "200", "pageNumber": str(pageNum)}, encoding="XML")
    response = parseString(data)
    itemNodes = response.getElementsByTagName('item');
    results = []
    for item in itemNodes:
        itemId = getSingleValue(item, 'itemId')
        itemTitle = getSingleValue(item, 'title')
        itemPrice = getSingleValue(item, 'currentPrice')
        itemEnds = getSingleValue(item, 'endTime')
        results.append((itemId, itemTitle, itemPrice, itemEnds))
    return results


def getCategory(query='', parentID=None, siteID='0'):
    lquery = query.lower()
    xml = "<?xml version='1.0' encoding='utf-8'?>" + \
          "<GetCategoriesRequest xmlns=\"urn:ebay:apis:eBLBaseComponents\">" + \
          "<RequesterCredentials><eBayAuthToken>" + \
          userToken + \
          "</eBayAuthToken></RequesterCredentials>" + \
          "<DetailLevel>ReturnAll</DetailLevel>" + \
          "<ViewAllNodes>true</ViewAllNodes>" + \
          "<CategorySiteID>" + siteID + "</CategorySiteID>"
    if parentID == None:
        xml += "<LevelLimit>1</LevelLimit>"
    else:
        xml += "<CategoryParent>" + str(parentID) + "</CategoryParent>"
    xml += "</GetCategoriesRequest>"
    data = sendRequest('GetCategories', xml)
    categoryList = parseString(data)
    catNodes = categoryList.getElementsByTagName('Category')
    for node in catNodes:
        catid = getSingleValue(node, 'CategoryID')
        name = getSingleValue(node, 'CategoryName')
        if name.lower().find(lquery) != -1:
            print catid, name


def getItem(itemID):
    xml = "<?xml version='1.0' encoding='utf-8'?>" + \
          "<GetItemRequest xmlns=\"urn:ebay:apis:eBLBaseComponents\">" + \
          "<RequesterCredentials><eBayAuthToken>" + \
          userToken + \
          "</eBayAuthToken></RequesterCredentials>" + \
          "<ItemID>" + str(itemID) + "</ItemID>" + \
          "</GetItemRequest>"
    data = sendRequest('GetItem', xml)
    print data
    result = {}
    response = parseString(data)
    result['title'] = getSingleValue(response, 'Title')
    sellingStatusNode = response.getElementsByTagName('SellingStatus')[0];
    result['price'] = getSingleValue(sellingStatusNode, 'CurrentPrice')
    result['bids'] = getSingleValue(sellingStatusNode, 'BidCount')
    seller = response.getElementsByTagName('Seller')
    result['feedback'] = getSingleValue(seller[0], 'FeedbackScore')

    attributeSet = response.getElementsByTagName('Attribute');
    attributes = {}
    for att in attributeSet:
        attID = att.attributes.getNamedItem('attributeID').nodeValue
        attValue = getSingleValue(att, 'ValueLiteral')
        attributes[attID] = attValue
    result['attributes'] = attributes
    return result


def makeLaptopDataset():
    searchResults = doSearch('laptop')
    result = []
    for r in searchResults:
        item = getItem(r[0])
        att = item['attributes']
        try:
            data = (float(att['12']), float(att['26444']),
                    float(att['26446']), float(att['25710']),
                    float(item['feedback'])
                    )
            entry = {'input': data, 'result': float(item['price'])}
            result.append(entry)
        except:
            print item['title'] + ' failed'
    return result


def main():
    laptops = doSearch('laptop')
    print laptops[0:10]
    # print getCategory('computers')
    # print getCategory('laptops', parentID=58058)
    # if laptops:
    #     print getItem(laptops[7][0])
    set = makeLaptopDataset()
    numpredict.knnestimate(set,(512,1000,14,40,1000))


if __name__ == "__main__": main()
