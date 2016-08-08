import ConfigParser

import akismet  # pip install akismet

config = ConfigParser.RawConfigParser()
config.read('config.ini')
defaultkey = config.get('config', 'defaultkey')
pageurl = config.get('config', 'pageurl')

defaultagent = "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.0.7) "
defaultagent += "Gecko/20060909 Firefox/1.5.0.7"


def isspam(comment, author, ipaddress, agent=defaultagent, apikey=defaultkey):
    am = akismet.Akismet(apikey, pageurl)
    try:
        valid = am.verify_key()
        if valid:
            cdata = {}
            cdata['user_ip'] = ipaddress
            cdata['user_agent'] = agent
            return am.comment_check(comment, data=cdata)
        else:
            print 'Invalid key'
            return False
    except akismet.AkismetError, e:
        print 'akismet error: %s' % e
        return False


def main():
    print isspam('Make money fast! Online Casino!', 'spammer@spam.com', '127.0.0.1')


if __name__ == "__main__": main()
