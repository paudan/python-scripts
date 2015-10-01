"""
A script to scrape and import company data from Google Finance into a PostgreSQL database. Supports use of proxy list and proxy rotation.
Use this script at your own risk!
Python 3 is required to run it
"""

from lxml.html import document_fromstring   # set STATICBUILD=true && pip install lxml && pip install cssselect
import postgresql.driver as pg_driver       # pip install py_postgresql
from postgresql import exceptions
import urllib.request as urllib
from urllib.error import HTTPError,URLError
import requests                             # pip install requests
import json
import re
import locale
from os import path
from time import sleep
from dateutil.parser import parse           # pip install python-dateutil
from configparser import ConfigParser

config = ConfigParser()
config.read(path.join(path.dirname(path.realpath(__file__)), 'config.cfg'))
username = config.get('dbsettings', 'user')
passwd = config.get('dbsettings', 'password')
server = config.get('dbsettings', 'host')
portval = config.getint('dbsettings', 'port')
dbname = config.get('dbsettings', 'database')

proxy_list = [x.strip() for x in config.get('proxy', 'proxies').split(sep=',')]


def get_ticker_list(exchange):
    try:
        db = pg_driver.connect(user=username, password=passwd, host=server, port=portval, database=dbname)
        ps = db.prepare('INSERT INTO google_finance.tickers (ticker, exchange, company_name) VALUES($1, $2, $3)')
        # Try to select all NASDAQ company data from a single page
        path = 'http://www.google.com/finance?q=[%28exchange+%3D%3D+%22{:s}%22%29]&restype=company&noIL=1&num=20000&ei=ul-rVYCFKI2cUvy-ibgC' \
            .format(exchange)
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
                            except Exception as e:
                                print("Data for ticker %s could not be inserted, reason: %s" % (ticker, format(e)))

        db.close()
    except exceptions.UniqueError as e:
        pass
    except exceptions.Exception as e:
        print("Connection could not be established")


def load_ticker_list(exchange, db):
    try:
        if not db:
            db = pg_driver.connect(user=username, password=passwd, host=server, port=portval, database=dbname)
        ps = db.prepare("SELECT ticker FROM google_finance.tickers where exchange='%s'" % (exchange))
        tickers = [r[0] for r in ps()]
        ps_parsed = db.prepare("SELECT ticker FROM google_finance.parsed")
        parsed = [r[0] for r in ps_parsed()]
        unchecked = [x for x in tickers if x not in set(parsed)]
        return unchecked
    except exceptions.Exception as e:
        print("Connection could not be established, error: %s" % (format(e)))
        return None


def parse_table(div):
    # Adopted from http://stackoverflow.com/a/9227796
    def get_float(st):
        # Remove anything not a digit, comma or period
        no_cruft = re.sub(r'[^\d,.-]', '', st)
        # Split the result into parts consisting purely of digits
        parts = re.split(r'[,.]', no_cruft)
        # ...and sew them back together
        if len(parts) == 1:
            # No delimeters found
            float_str = parts[0]
        elif len(parts[-1]) != 2:
            # >= 1 delimeters found. If the length of last part is not equal to 2, assume it is not a decimal part
            float_str = ''.join(parts)
        else:
            float_str = '%s%s%s' % (''.join(parts[0:-1]), locale.localeconv()['decimal_point'], parts[-1])
        try:
            result = float(float_str)
            return result
        except:
            return None

    result = {}
    for table in div.cssselect('table'):
        if 'fs-table' in table.get('id'):
            data = {}
            header = []
            start = True
            for th in table.cssselect('th'):
                # Skip first table header entry
                if not start:
                    match = re.search(r'\d{4}-\d{2}-\d{2}', th.text_content().strip())
                    header.append(match.group())
                else:
                    start = False
            for tr in table.cssselect('tr'):
                values = []
                name = ''
                for td in tr.cssselect('td'):
                    if 'lft' in td.get('class'):
                        name = td.text_content().strip()
                    elif 'r' in td.get('class'):
                        if len(td.cssselect('span')) > 0:
                            values.append(td.cssselect('span')[0].text_content().strip())
                        else:
                            values.append(td.text_content().strip())
                if name != '':
                    data[name] = values
            for i in range(len(header)):
                entry = {}
                for name in data:
                    val = get_float(data[name][i])
                    if val:
                        entry[name] = val
                result[header[i]] = entry
            return result


def scrape():
    def insert_data(ps, ticker, type, period, div):
        results = parse_table(div)
        for date in results:
            data = json.dumps(results[date], indent=1, sort_keys=True)
            if db and type and ticker and data:
                try:
                    print('Inserting values ({:s}, {:s}, {:s}, {:b})'.format(type, date, ticker, period))
                    ps(type, parse(date), ticker, data, period)
                except exceptions.Exception as e:
                    print("Connection could not be established, error: %s" % (format(e)))
                except Exception as e:
                    print("Data for {ticker: %s, type: %s, date: %s, period: %s} could not be inserted, reason: %s" %
                          (ticker, type, date, period, format(e)))

    def rotate_proxy(s, ind):
        ind = 0 if ind == len(proxy_list)-1 else ind + 1
        s.proxies = {"http": proxy_list[ind]}


    db = pg_driver.connect(user=username, password=passwd, host=server, port=portval, database=dbname)
    ps = db.prepare('INSERT INTO google_finance.financial_data ("type", issue_date, ticker, "data", annual) VALUES($1, $2, $3, $4, $5)')
    ps_parsed = db.prepare('INSERT INTO google_finance.parsed(ticker) VALUES ($1)')
    exchanges = [r[0] for r in db.query('select distinct exchange from google_finance.tickers')]
    if exchanges is None: return
    s = requests.Session()
    ind = 0
    s.proxies = {"http": proxy_list[ind]}
    try:
        for exchange in exchanges:
            # tickers = get_ticker_list(exchange)
            tickers = load_ticker_list(exchange, db)
            if tickers is None: return
            counter = 0
            for ticker in tickers:
                # Check if have processed this ticker
                checked = False
                while not checked:
                    path = 'https://www.google.com/finance?q={:s}%3A{:s}&fstype=ii&ei=1Q7qVfGwKcyisAHQn5DADw'\
                        .format(exchange, ticker)
                    content = s.get(path).text
                    if content:
                        doc = document_fromstring(content)
                        # Check if main menu element exists - otherwise, Google captcha could have been called
                        sel = doc.cssselect('div#gf-nav')
                        if sel:
                            checked = True
                            print(ticker)
                            for div in doc.cssselect('div'):
                                if div.get('id') == 'incinterimdiv':
                                    insert_data(ps, ticker, 'income_statement', False, div)
                                elif div.get('id') == 'incannualdiv':
                                    insert_data(ps, ticker, 'income_statement', True, div)
                                elif div.get('id') == 'balinterimdiv':
                                    insert_data(ps, ticker, 'balance', False, div)
                                elif div.get('id') == 'balannualdiv':
                                    insert_data(ps, ticker, 'balance', True, div)
                                elif div.get('id') == 'casinterimdiv':
                                    insert_data(ps, ticker, 'cash_flow_statement', False, div)
                                elif div.get('id') == 'casannualdiv':
                                    insert_data(ps, ticker, 'cash_flow_statement', True, div)
                            # We do not want to check this ticker several times, if we would need to restart,
                            # so we insert its value into 'parsed' file
                            ps_parsed(ticker)
                            counter += 1
                            if counter % 1000 == 0:
                                sleep(600)
                                rotate_proxy(s, ind)
                        else:
                            # Google identified a robot - postpone processing for some longer time
                            print('Page does not contain financials information and menu. Pausing for 30 min... ')
                            sleep(1800)
                            rotate_proxy(s, ind)
    except URLError as e:
        pass
    except HTTPError as e:
        if e.code == 503:
            rotate_proxy(s, ind)
    finally:
        db.close()


def main():
    scrape()


if __name__ == "__main__": main()
