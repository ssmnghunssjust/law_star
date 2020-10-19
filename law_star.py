# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   File Name：     law_star.py 
   Description :   法律之星网站，使用协程池，爬取搜索结果的前10页内容。
   Author :        LSQ
   date：          2020/10/19
-------------------------------------------------
   Change Activity:
                   2020/10/19: None
-------------------------------------------------
"""
import gevent
from gevent import monkey, pool

monkey.patch_all()
import requests
import time

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from lxml.etree import HTML
from urllib.parse import urljoin


class LawStarCrawler(object):
    '''
    开启爬取前需要手动获取cookie，只取loginuser和loginpass字段即可。如：'Cookie': 'loginuser=13121174131; loginpass=CF9EAE1EDE7D5E78SY9H342FB22F038'
    '''

    def __init__(self, cookie: str = None, word: str = None):
        self.base_url = 'http://law1.law-star.com'
        self.url = 'http://law1.law-star.com/search?kw={}&dbt=chl&dbt=lar&ps=50&sort=imp&p=1'.format(word)
        self.headers = {
            'Cookie': cookie,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36',
        }
        self.mongo = MongoClient('mongodb://127.0.0.1:27017')
        self.collection = self.mongo['law_star']['data']
        self.pool = pool.Pool()

    def __del__(self):
        self.mongo.close()

    def _get_response(self, url=None):
        if url is None:
            # url = urlencode(self.url)
            print(f'正在爬取链接：{self.url}')
            resp = requests.get(self.url, headers=self.headers)
            if resp.status_code == 200:
                return resp
            else:
                raise Exception(f'{resp.status_code}')
        else:
            url = urljoin(self.base_url, url)
            print(f'正在爬取链接：{url}')
            resp = requests.get(url, headers=self.headers)
            if resp.status_code == 200:
                return resp
            else:
                raise Exception(f'{resp.status_code}')

    def _get_text(self, response):
        return response.content.decode()

    def _get_data(self, html):
        html = HTML(html)
        li_list = html.xpath('//ul[@class="list05"]/li')
        data = dict()
        item_list = list()

        # 同步操作
        # for li in li_list:
        #     item = self._parse_detail(li)
        #     item_list.append(item)
        #     time.sleep(3)

        # 协程池异步
        coroutine_list = [self.pool.spawn(self._parse_detail, li) for li in li_list]
        gevent.joinall(coroutine_list)
        for coroutine in coroutine_list:
            item_list.append(coroutine.value)

        data['item_list'] = item_list
        data['next_url'] = html.xpath('//form[@name="pageform"]/div/a[@class="xyy"]/@href').pop()
        return data

    def _parse_detail(self, li):
        item = dict()
        item['_id'] = li.xpath('./div[@class="div05"]/h2/a/@rjs8').pop()
        item['url'] = urljoin(self.base_url, li.xpath('./div[@class="div05"]/h2/a[1]/@href').pop())
        item['title'] = li.xpath('./div[@class="div05"]/h2/a[1]/@title').pop()
        response = self._get_response(item['url'])
        text = self._get_text(response)
        detail_html = HTML(text)
        # 法规文号
        item['fgwh'] = detail_html.xpath('/html/body/div[8]/div/div/div[3]/ul/li[2]/p/text()') if len(
            detail_html.xpath('/html/body/div[8]/div/div/div[3]/ul/li[2]/p/text()')) > 0 else None
        # 发布日期
        item['fbrq'] = detail_html.xpath('//p[@id="tdat"]/text()') if len(
            detail_html.xpath('//p[@id="tdat"]/text()')) > 0 else None
        # 实施日期
        item['ssrq'] = detail_html.xpath('/html/body/div[8]/div/div/div[3]/ul/li[4]/p/text()') if len(
            detail_html.xpath('/html/body/div[8]/div/div/div[3]/ul/li[4]/p/text()')) > 0 else None
        # 发布部门
        item['fbbm'] = detail_html.xpath('//p[@id="tdpt"]/text()') if len(
            detail_html.xpath('//p[@id="tdpt"]/text()')) > 0 else None
        # 效力等级
        item['xldj'] = detail_html.xpath('/html/body/div[8]/div/div/div[3]/ul/li[6]/p/text()') if len(
            detail_html.xpath('/html/body/div[8]/div/div/div[3]/ul/li[6]/p/text()')) > 0 else None
        # 正文
        item['maintext'] = detail_html.xpath('//div[@id="maintext"]/text()') if len(
            detail_html.xpath('//div[@id="maintext"]/text()')) > 0 else None
        return item

    def _save_data(self, data):
        for each in data:
            try:
                self.collection.insert_one(each)
            except DuplicateKeyError as e:
                print(e)

    def run(self):
        url = None
        page = 1
        print('开始爬取')
        start = time.time()
        while True:
            print(f'第{page}页***')
            start_time = time.time()
            # 1 发送首页请求，获取响应
            response = self._get_response(url)
            # 2 解析响应为text
            html = self._get_text(response)
            # 3 提取数据
            data = self._get_data(html)
            # 4 保存数据
            self._save_data(data['item_list'])
            # 5 下页请求url
            url = data['next_url']
            page += 1
            if page > 10:
                break
            end_time = time.time()
            print(f'爬取这一页共耗时{end_time - start_time}秒')
        end = time.time()
        print('爬取结束，总耗时：{:.2f}秒'.format(end - start))


if __name__ == '__main__':
    crawler = LawStarCrawler(cookie='', word='劳动法')
    crawler.run()
