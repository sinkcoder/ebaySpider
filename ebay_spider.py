#!/usr/bin/env python
# coding:utf-8
import requests
from bs4 import BeautifulSoup
import itchat
import sys
import time
import cPickle
import os
import logging

SAVE_PATH = 'ebaySpiderData'
KEYWORDS = ['b w speakers', 'dynaudio 1.3']
INTERVAL = 100
SEND_TO = 'someBody'


logging.basicConfig(level=logging.INFO,
                    filename='output.log',
                    datefmt='%Y/%m/%d %H:%M:%S',
                    format='%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(module)s - %(message)s')
logger = logging.getLogger(__name__)


def check_page(keywords, path):
    url = 'https://www.ebay.com/sch/i.html?_from=R40'
    headers = {
            'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 \
                    (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36"
            }
    items_set_dict = {}
    for keyword in keywords:
        params = {
                '_nkw': keyword,
                '_ipg': 200
                }

        try:
            r = requests.get(url, params, headers=headers)
        except Exception as e:
            logger.error(str(e))
            continue
        logger.info("Searching for %s new items." % keyword)
        soup = BeautifulSoup(r.content, 'lxml')
        pages_url = gat_pages_url(soup)
        items = soup.find_all(name='li', attrs={'class': 'sresult lvresult clearfix li'})
        for page_url in pages_url:
            try:
                r = requests.get(page_url, headers=headers)
            except Exception as e:
                logger.error(str(e))
                continue
            temp_soup = BeautifulSoup(r.content, 'lxml')
            temp_items = temp_soup.find_all(
                    name='li', attrs={'class': 'sresult lvresult clearfix li'}
                    )
            items.extend(temp_items)
        items_list = map(get_item_attrs, items)
        items_set = set(items_list)
        items_set_dict[keyword] = items_set
    with open(path, 'wb') as f:
        cPickle.dump(items_set_dict, f)
    return items_set_dict


def gat_pages_url(soup):
    pagination_tags = soup.find_all(
            name='td', attrs={'class': 'pages'}
            )
    return [tag.a.get('href') for tag in pagination_tags[1:]]


def get_item_attrs(item_tag):
    item_title = item_tag.h3.a.text
    item_price = item_tag.find(
            name='li', attrs={'class': 'lvprice prc'}
            ).span.text.lstrip('\n')
    item_url = item_tag.a.get('href', 'N/A')
    return (item_title, item_price, item_url)


def wechat_client():
    itchat.auto_login(hotReload=True)
    friends = itchat.search_friends(nickName=SEND_TO.decode('utf8'))
    if friends:
        to_user = friends[0]
        to_user_name = to_user.get('UserName')
    else:
        to_user_name = 'filehelper'
    new_items_set = legacy_items_set = set()
    legacy_items_set_dict = {}
    if os.path.exists(SAVE_PATH):
        with open(SAVE_PATH, 'rb') as f:
            legacy_items_set_dict = cPickle.load(f)
    while True:
        latest_items_set_dict = check_page(KEYWORDS, SAVE_PATH)
        for key in latest_items_set_dict.keys():
            if legacy_items_set_dict.has_key(key):
                new_items_set = latest_items_set_dict.get(key) - legacy_items_set_dict.get(key)
            legacy_items_set_dict[key] = latest_items_set_dict.get(key)
            if new_items_set:
                message = '%s: Found %d new items at %s' \
                        % (key, len(new_items_set), time.ctime())
                logger.info("Found %d new items." % len(new_items_set))
                for index, new_item in enumerate(new_items_set):
                    message += "\n\n" + str(index+1) + "." + "\n".join(new_item)
                logger.info("Sending wechat message to %s." % to_user_name)
                itchat.send(message, toUserName=to_user_name)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    reload(sys)
    sys.setdefaultencoding('utf-8')
    wechat_client()
