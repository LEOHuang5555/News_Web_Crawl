
import yfinance as yf
import matplotlib.pyplot as plt
plt.style.use('seaborn')
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

# 試題 2 鉅亨網
class anue():
    def __init__(self, url, page:str, start:str = str(int((datetime.datetime.utcnow()-datetime.timedelta(1)).timestamp())), end:str =str(int(datetime.datetime.utcnow().timestamp())-1)):
        self.url = url
        self.page = page
        self.start = start
        self.end = end
        self.prefix = 'https://news.cnyes.com/news/id/'
        
    def get_response(self):
        payload = {
        'limit':'30',
        'startAt': self.start,
        'endAt': self.end,
        'page': self.page,
        'startAt': self.start,
        'endAt': self.end,
        'limit': '30'
        }
        self.payload = payload
        self.response = rq.get(self.url, params = self.payload)
    
    def get_total_pages(self):
        self.get_response()
        self.data = self.response.json()
        total = self.data['items']['total']
        per_page = self.data['items']['per_page']
        self.total_pages = int(total/per_page)
    
    def get_titles_urls_per_page(self):
        news_urls = []
        news_titles = []
        for i in self.data['items']['data']:
            news_urls += [i['newsId']]
            news_titles += [i['title']]
        data = {
            'news_urls':news_urls,
            'news_titles':news_titles
            }
        return pd.DataFrame(data)
    
    def get_all_titles_urls(self):
        self.get_total_pages()
        data = pd.DataFrame()
        for i in range(1, self.total_pages+1):
            self.page = i
            self.get_response()
            temp = self.get_titles_urls_per_page()
            data = pd.concat([data, temp])
        data = data.reset_index(drop=True)
        data['news_urls'] = data['news_urls'].apply(lambda x:self.prefix+str(x))
        return data
# 試題 2 工商時報
class ctee():
    def __init__(self, url, page:str, start:str = str(int((datetime.datetime.utcnow()-datetime.timedelta(1)).timestamp())), end:str =str(int(datetime.datetime.utcnow().timestamp())-1)):
        self.url = url
        self.page = page
        self.start = start
        self.end = end
        self.prefix = url

    def get_html(self):
        self.response = rq.get(self.url)
        self.soup = bs(self.response.text, 'html.parser')
    
    def get_total_pages(self):
        self.total_pages = 0
        while self.total_pages == 0:
            self.get_html()
            for i in self.soup.find_all('a',{'class':'page-numbers'}):
                if i.text != '下一頁 »':
                    self.total_pages = i.text
            self.total_pages = int(self.total_pages)

    def get_titles_urls_per_page(self):
        data = pd.DataFrame()
        # times = 0
        while len(data) == 0:
            self.get_html()
            links = self.soup.find_all('a',{'style':'color:#777777;text-decoration: none;'})
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
            # times+=1
            # print(times)

        return data

    def get_all_titles_urls(self):
        self.get_total_pages()
        data = pd.DataFrame()
        for i in range(1, self.total_pages+1):
            if i == 1:
                temp = self.get_titles_urls_per_page()
            else:
                self.url = self.prefix +'/page/'+str(i)
                temp = self.get_titles_urls_per_page()
            data = pd.concat([data, temp])
        return data

# 試題 3
class crawl_self_acc():
    def __init__(self, url, stk, year):
        self.url = url
        self.stk = stk
        self.year = year
        self.freq = 'Q'
    def get_payload(self):
        self.payload = {
                'encodeURIComponent':'1',
                'run':'Y',
                'step': '1',
                'CK2': '3',
                'BK1': '2',
                'TYPEK':'sii', 
                'YEAR':self.year, 
                'COMP': self.stk,
                'firstin': 'true'
        }
        if self.freq == 'M':
            self.payload['CK2'] = '1' 

    def get_response(self):
        self.get_payload()
        self.response = rq.get(self.url, params=self.payload)
        self.soup = bs(self.response.content, 'html.parser') 
    
    def extract_number(self, lst):
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
    
    def get_self_acc_sales(self):
        self.get_response()
        if len(self.soup.find_all('font',{'color':'red'})) > 0:
            self.freq = 'M'
            self.get_response()

        self_acc_sales = self.soup.find_all('td',{'align':'right', 'class':'odd', 'width':''})
        # 最新一季資料
        if self.freq == 'Q':
            latest = self.extract_number(self_acc_sales[-1])
        else:
            latest = self.extract_number(self_acc_sales[-3:])

        code_name = [i for i in self.soup.find_all('h3') if '公司名稱' in str(i)]
        # 取得 股票名稱
        # \n表示換行
        temp = str(code_name[0]).split('\r\n')[1]
        self.name = temp.split(' ')[0]
        #
        data = {
            '代碼':self.stk,
            '股名':self.name,
            '自結上一季獲利':latest
        }
        result = pd.DataFrame([data])
        return result