import time
import hashlib
import hmac
import facebook     # pip install facebook-sdk
from ConfigParser import ConfigParser

config = ConfigParser()
config.read('fbconfig.ini')
apikey = config.get('fbconfig-analytics', 'apikey')
secret = config.get('fbconfig-analytics', 'secret')
token = config.get('fbconfig-analytics', 'access_token')

def getsinglevalue(node, tag):
    nl = node.getElementsByTagName(tag)
    if len(nl) > 0:
        tagNode = nl[0]
        if tagNode.hasChildNodes():
            return tagNode.firstChild.nodeValue
    return ''


def callid():
    return str(int(time.time() * 10))


class fbsession:

    def __init__(self):
        self.graph = facebook.GraphAPI(token)

    def genAppSecretProof(self, app_secret, access_token):
        h = hmac.new (
            app_secret.encode('utf-8'),
            msg=access_token.encode('utf-8'),
            digestmod=hashlib.sha256
        )
        return h.hexdigest()

    def getfriends(self):
        proof =  self.genAppSecretProof(secret, token)
        profile = self.graph.get_object("me", appsecret_proof=proof)
        friends = self.graph.get_object("me/taggable_friends", appsecret_proof=proof)
        friend_list = [friend['name'] for friend in friends['data']]
        print friend_list
        return friend_list


def main():
    s=fbsession()
    friends=s.getfriends()
    friends[1]


if __name__ == "__main__": main()