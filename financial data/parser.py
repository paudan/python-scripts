from lxml.html import document_fromstring, tostring   # set STATICBUILD=true && pip install lxml (Python 3.4), pip install cssselect
import postgresql.driver as pg_driver                 # pip install py_postgresql (Python 3.4)
import urllib.request as urllib
from configparser import ConfigParser

config = ConfigParser()
config.read('config.cfg')
username = config.get('dbsettings', 'user')
passwd = config.get('dbsettings', 'password')
server = config.get('dbsettings', 'host')
portval = config.getint('dbsettings', 'port')
dbname = config.get('dbsettings', 'database')

def get_ticker_list():
    # try:
    db = pg_driver.connect(user=username, password=passwd,
                           host=server, port=portval, database=dbname)
    ps = db.prepare('INSERT INTO external_data.tickers_gf (ticker, exchange, company_name) VALUES($1, $2, $3)')
    path = 'http://www.google.com/finance?q=[%28exchange+%3D%3D+%22NASDAQ%22%29]&restype=company&noIL=1&num=20000&ei=ul-rVYCFKI2cUvy-ibgC'
    content = urllib.urlopen(path).read().decode('utf-8')
    doc = document_fromstring(content)
    for div in doc.cssselect('table'):
        if div.get('class') == 'gf-table company_results':
            for tr in div.cssselect('tr'):
                if tr.get('class') == 'snippet':
                    ticker = []
                    company = []
                    exchange = []
                    for td in tr.cssselect('td'):
                        if td.get('class') == 'localName nwp':
                            company = td.text_content().strip()
                        elif td.get('class') == 'exch':
                            exchange = td.text_content().strip()
                        elif td.get('class') == 'symbol':
                            ticker = td.text_content().strip()
                    if ticker != []:
                        try:
                            print('Inserting values ({:s}, {:s}, {:s})'.format(ticker, exchange, company))
                            ps(ticker, exchange, company)
                        except:
                            print("Data for ticker %s could not be inserted" % (ticker))

    db.close()

    # except:
    #    print("Connection could not be established")


def load_ticker_list():
    l = []
    try:
        db = pg_driver.connect(user=username, password=passwd, host=server, port=portval, database=dbname)
        ps = db.prepare('SELECT ticker FROM external_data.tickers_gf')
        res = ps()
        for r in res:
            l.append(r[0])
        db.close()
    except:
        print("Connection could not be established")
    return l


def parse_table(div):
    result = {}
    for table in div.cssselect('table'):
        if table.get('id') == 'fs-table':
            for tr in table.cssselect('tr'):
                values = []
                name = ''
                for td in tr.cssselect('td'):
                    if td.get('class') == 'lft lm':
                        name = td.text_content().strip()
                    elif td.get('class') == 'r' or td.get('class') == 'r rm':
                        values.append(td.text_content().strip())
                if name != '':
                    result[name] = values
    return result


def main():
    # l = load_ticker_list()
    # print(l)
    path = 'https://www.google.com/finance?q=NASDAQ%3AMSFT&fstype=ii&ei=1Q7qVfGwKcyisAHQn5DADw'
    content = urllib.urlopen(path).read().decode('utf-8')
    doc = document_fromstring(content)
    for div in doc.cssselect('div'):
        if div.get('id') == 'incinterimdiv':
            print("\nQuarterly income statement:\n")
            print(parse_table(div))
        elif div.get('id') == 'incannualdiv':
            print("\nAnnual income statement:\n")
            print(parse_table(div))
        elif div.get('id') == 'balinterimdiv':
            print("\nQuarterly balance:\n")
            print(parse_table(div))
        elif div.get('id') == 'balannualdiv':
            print("\nAnnual balance:\n")
            print(parse_table(div))
        elif div.get('id') == 'casinterimdiv':
            print("\nQuarterly cash flow statement:\n")
            print(parse_table(div))
        elif div.get('id') == 'casannualdiv':
            print("\nAnnual cash flow statement:\n")
            print(parse_table(div))


if __name__ == "__main__": main()
