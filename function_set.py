
import yfinance as yf
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
import requests as rq
from bs4 import BeautifulSoup as bs
import pandas as pd
import datetime
import re

def get_stock(symbols):
    def craw_yf(origin_ticker, new_ticker):
        stk = yf.Ticker(new_ticker)
        data = stk.history()
        data['ROI'] = ((data['Close']/data['Close'].shift(1))-1)*100
        data['代碼'] = origin_ticker
        res = data.tail(1)[['代碼','Close','ROI','Volume', 'High','Low']]
        res = res.rename(columns ={
                'Close':'收盤價',
                'ROI':'日漲跌幅(%)',
                'Volume':'日成交量',
                'High':'日最高價',
                'Low':'日最低價'
                })
        return res
    # 
    # 更改指數的 ticker
    if str(symbols).__contains__('#'):
        if str(symbols) =='#SOXX':
            new_symbol = '^SOX'
        else:
            new_symbol = str(symbols).replace('#','^')
        # 
        data = craw_yf(str(symbols), new_symbol)
    else:
        data = craw_yf(str(symbols), str(symbols))
    return data
start = str(int(datetime.datetime(2023, 2, 21).timestamp()))
end = str(int(datetime.datetime(2023, 2, 23).timestamp())-1)
def get_anue_titles_urls(url, pages:str, start:str = start, end:str =end) :
    pages = get_anue_total_page(url, pages, start, end)
    data = pd.DataFrame()
    for i in range(1, pages+1):
        response = request_url(url, i, start, end)
        temp = get_titles(response.json())
        data = pd.concat([data, temp])
    data = data.reset_index(drop=True)
    data['news_urls'] = data['news_urls'].apply(get_anue_news_urls)
    return data

def request_url(url, pages:str, start:str = start, end:str =end):
    payload = {
    'limit':'30',
    'startAt': start,
    'endAt': end,
    'page': pages,
    'startAt': start,
    'endAt': end,
    'limit': '30'
    }
    response = rq.get(url, params=payload)
    return response

def get_titles(data):
    news_urls = []
    news_titles = []
    for i in data['items']['data']:
        news_urls += [i['newsId']]
        news_titles += [i['title']]
    data = {
        'news_urls':news_urls,
         'news_titles':news_titles
         }
    return pd.DataFrame(data)

def get_anue_total_page(url, pages, start:str = start, end:str = end):
    response = request_url(url, pages, start, end)
    data = response.json()
    total = data['items']['total']
    per_page = data['items']['per_page']
    return int(total/per_page)

def get_anue_news_urls(word):
    prefix = 'https://news.cnyes.com/news/id/'
    return prefix + str(word)
    
    

def get_html(url):
    response = rq.get(url)
    soup = bs(response.text, 'html.parser')
    return soup

def crawl_ctee_titles(url):
    data = pd.DataFrame()
    while len(data) == 0:
        soup = get_html(url)
        links = soup.find_all('a',{'style':'color:#777777;text-decoration: none;'})
        urls = []
        titles = []
        for link in links:
            urls.append(link.get('href'))
            titles.append(link.text.strip())
        data = {
            'news_urls':urls,
            'news_titles':titles
        }
        data = pd.DataFrame(data)

    return data

def get_ctee_pages(url):
    final_pages = 0
    while final_pages == 0:
        soup = get_html(url)
        for i in soup.find_all('a',{'class':'page-numbers'}):
            if i.text != '下一頁 »':
                final_pages = i.text
        final_pages = int(final_pages)
    return final_pages

def get_ctee_titles_urls(url):
    total_pages = get_ctee_pages(url)
    data = pd.DataFrame()
    for i in range(1, total_pages+1):
        if i == 1:
            temp = crawl_ctee_titles(url)
        else:
            new_url = url +'/page/'+str(i)
            temp = crawl_ctee_titles(new_url)
        data = pd.concat([data, temp])
    return data


def get_self_acc_sales(stk, year):
    # 公開資訊觀測站 自結損益公告-季申報
    url = 'https://mops.twse.com.tw/mops/web/ajax_t138sb02'
        
    # 先從季公告開始，若季公告沒資料則去爬月公告
    freq = 'Q'
    soup = request_url(url, stk, year, freq)
    if len(soup.find_all('font',{'color':'red'})) > 0:
        freq = 'M'
        soup = request_url(url, stk, year, freq)
        # print(soup)
    self_acc_sales = soup.find_all('td',{'align':'right', 'class':'odd', 'width':''})
    # 最新一季資料
    if freq == 'Q':
        latest = extract_number(self_acc_sales[-1])
    else:
        latest = extract_number(self_acc_sales[-3:])

    code_name = [i for i in soup.find_all('h3') if '公司名稱' in str(i)]
    # 取得 股票名稱
    # \n表示換行
    temp = str(code_name[0]).split('\r\n')[1]
    name = temp.split(' ')[0]
    #
    data = {
        '代碼':stk,
        '股名':name,
        '自結上一季獲利':latest
    }
    result = pd.DataFrame([data])
    return result

def get_payload(stk, year, freq):
        payload = {
                'encodeURIComponent':'1',
                'run':'Y',
                'step': '1',
                'CK2': '3',
                'BK1': '2',
                'TYPEK':'sii', 
                'YEAR':year, 
                'COMP': stk,
                'firstin': 'true'
        }
        if freq == 'M':
            payload['CK2'] = '1'
        return payload

def request_url(url, stk, year, freq):
    payload = get_payload(stk, year, freq)
    response = rq.get(url, params=payload)
    soup = bs(response.content, 'html.parser') 
    return soup

def extract_number(lst):
    def extract_num(item):
        item = str(item)
        number = re.search(r'\d[\d,]*\d', item).group()
        number_str = number.replace(',','').replace('-','')
        number = int(number_str)
        if '-' in item:
            number = (-1)*number
        return number
    numbers = list(map(extract_num, lst))
    return sum(numbers)