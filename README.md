# law_star
## 法律之星网站，使用协程池，爬取搜索结果的前10页内容。
## 开启爬取前需要手动获取cookie，只取loginuser和loginpass字段即可。如：'Cookie': 'loginuser=13121174131; loginpass=CF9EAE1EDE7D5E78SY9H342FB22F038'
## 使用方法
```python
crawler = LawStarCrawler(cookie='', word='劳动法')
crawler.run()
