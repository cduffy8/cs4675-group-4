import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.crawler import CrawlerProcess
from bs4 import BeautifulSoup
from pymongo import MongoClient


class MySpider(scrapy.Spider):
    name = 'my_spider'
    start_urls = ['https://nextjs.org/docs/app']
    visited_urls = set()

    def __init__(self, *args, **kwargs):
        super(MySpider, self).__init__(*args, **kwargs)
        self.client = MongoClient('mongodb+srv://bxrodgers1:CS4675@cluster0.6u3n5.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
        self.db = self.client['web_crawler']
        self.collection = self.db['crawl_data']
        
        # Clear existing data
        self.collection.delete_many({})
        self.visited_urls = set()

    def parse(self, response):
        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove script and style tags
        for tag in soup(['script', 'style', 'footer', 'header', 'nav']):
            tag.extract()

        # Cleaned HTML content
        cleaned_html = soup.get_text(separator=' ', strip=True)
        cleaned_html = cleaned_html.split(" Was this helpful? supported. Send")[0]

        data = {
            'url': response.url,
            'title': response.css('title::text').get(),
            'html': cleaned_html
        }

        # Save to MongoDB
        self.collection.insert_one(data)

        yield data

        # Extract and follow links
        link_extractor = LinkExtractor()
        for link in link_extractor.extract_links(response):
            if link.url.startswith('https://nextjs.org/docs/app') and "#" not in link.url:
                if link.url not in self.visited_urls:
                    self.visited_urls.add(link.url)
                    yield scrapy.Request(url=link.url, callback=self.parse)

    def closed(self, reason):
        self.client.close()


if __name__ == '__main__':
    process = CrawlerProcess()
    process.crawl(MySpider)
    process.start()
