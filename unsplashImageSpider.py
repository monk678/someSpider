# -*- coding: utf-8 -*-
# @Time    : 2018年11月16日 4:27 PM
# @Author  : 李思原
# @Email   : shulisiyuan@163.com
# @File    : unsplashImageSpider.py
# @Software: PyCharm
# @Describe: 爬取unsplash上的图片.

import http.client
import hashlib
from urllib import parse
import random
import json
import langid
import requests
import os
import datetime
import threading
import time
from multiprocessing import Pool
from retry import retry

fileSaveBasePath = './unsplashImageSpider/'


# type表示翻译类型
# type=1表示中文翻译为英文
# type=2表示英文翻译为中文
def Chinese2English(word='朋友', type=1):
    appid = '20180901000201564'  # 你的appid
    secretKey = 'fV2gfeIQtEEVgol3PJ9R'  # 你的密钥

    httpClient = None
    myurl = '/api/trans/vip/translate'
    fromLang = 'zh'
    toLang = 'en'
    salt = random.randint(32768, 65536)

    sign = appid + word + str(salt) + secretKey
    m1 = hashlib.new('md5')
    m1.update(sign.encode('utf-8'))
    sign = m1.hexdigest()
    if type == 1:
        myurl = myurl + '?appid=' + appid + '&q=' + parse.quote(word) + '&from=zh&to=en' + '&salt=' + str(
            salt) + '&sign=' + sign
    elif type == 2:
        myurl = myurl + '?appid=' + appid + '&q=' + parse.quote(word) + '&from=en&to=zh' + '&salt=' + str(
            salt) + '&sign=' + sign

    try:
        httpClient = http.client.HTTPConnection('api.fanyi.baidu.com')
        httpClient.request('GET', myurl)

        # response是HTTPResponse对象
        response = httpClient.getresponse()
        responseData = json.loads(response.read().decode())
        word = responseData['trans_result'][0]['dst']
        # print(responseData)
        return word
    except Exception as e:
        print(e)
    finally:
        if httpClient:
            httpClient.close()


# 判断语言种类，并获得文字的中英文
def judgeLanguageType(word):
    languageType = langid.classify(word)[0]

    if languageType == 'en':
        wordEnglish = word
        wordChinese = Chinese2English(word=word, type=2)
    else:
        wordChinese = word
        wordEnglish = Chinese2English(word=word, type=1)

    return wordEnglish, wordChinese


# 根据URL地址，文件名，文件存储路径下载文件
@retry(tries=5, delay=1, backoff=2, max_delay=8, jitter=1)
def saveFile(path, file_name, url):
    if not os.path.exists(os.path.join(path, file_name)):
        data = requests.get(url).content
        if data == None:
            return
        if not os.path.exists(path):
            os.makedirs(path)

        if (not path.endswith("/")):
            path = path + "/"
        file = open(path + file_name, "wb")
        file.write(data)
        file.flush()
        file.close()


# 爬取图片
def getImg(wordEnglish='boy', wordChinese='男孩', pageNum=1):
    url = "https://unsplash.com/napi/search/photos"

    headers = {
        'accept': "*/*",
        'accept-encoding': "gzip, deflate, br",
        'accept-language': "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        'cookie': "xp-search-cervantes-v1=experiment; _ga=GA1.2.679081907.1542356444; _gid=GA1.2.1314320132.1542356444; lsnp=sigsrn9xi0A; uuid=83b1b910-e978-11e8-b31c-79173615a02c; xpos=%7B%7D; lux_uid=154235838759040539; _sp_ses.0295=*; _gat=1; _sp_id.0295=9b24233c-ddff-4962-bb9b-29642f7eea2a.1542356445.2.1542358413.1542356505.499207fd-2257-46f0-b05f-b9f8a43edd51",
        'dpr': "2",
        'referer': "https://unsplash.com/search/photos/boy",
        'user-agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36",
        'viewport-width': "813"
    }

    for page in range(1, int(pageNum) + 1):
        print('正在爬取关键字：%s_%s第%s页' % (wordChinese, wordEnglish, page))
        querystring = {"query": '%s' % wordEnglish, "page": "%s" % page, "per_page": "30"}
        response = requests.request("GET", url, headers=headers, params=querystring)
        responseData = response.text
        # print(responseData)

        pageNum = min(int(pageNum), int(json.loads(responseData)['total_pages']))
        responseDatas = json.loads(responseData)['results']

        def action(arg):
            startime = datetime.datetime.now()
            img = responseDatas[arg]
            try:
                imgDescription = img['description']
            except AttributeError:
                return
            imgUrl = img['urls']
            # print('关键词：%s_%s>>页面:%s爬取线程%s>>标题：%s' % (wordChinese, wordEnglish, page, arg, imgDescription))

            fileSavePath = os.path.join(fileSaveBasePath, '%s_%s') % (wordChinese, wordEnglish)
            fileSaveName = '%s_%s_%s.jpg' % (wordChinese, wordEnglish, imgDescription)

            # 图片从大到小尺寸：raw,full,regular,small,thumb
            saveFile(path=fileSavePath, file_name=fileSaveName, url=imgUrl['regular'])
            endtime = datetime.datetime.now()
            print('###关键词：%s_%s>>页面%s图片%s耗时：%s' % (wordChinese, wordEnglish, page, arg, endtime - startime))

        for i in range(len(responseDatas)):
            # print('*******关键词：%s_%s页面%s正在启动线程%s' % (wordChinese, wordEnglish, page, i))
            time.sleep(1)
            t = threading.Thread(target=action, args=(i,))
            t.start()


# 处理爬取图片页面数
def spiderPageNum(keywords):
    try:
        pageNum = int(input('请输入要爬取主题"%s"的页面数目(每页大约30张图片): ' % keywords))
    except ValueError:
        print('输入错误,请输入数字')
        pageNum = spiderPageNum()
    return pageNum


if __name__ == '__main__':
    keywords = input('请输入要下载的关键字(使用空格分开关键字): ').split(' ')
    print('共有%s个关键字' % str(len(keywords)))
    pageNum = spiderPageNum(keywords)


    def getImgByWord(keyword):
        wordEnglish, wordChinese = judgeLanguageType(word=keyword)
        getImg(wordEnglish=wordEnglish, wordChinese=wordChinese, pageNum=pageNum)
        print('\n>>>>>>>>>>关键词：%s爬取完毕！\n' % keyword)


    p = Pool(8)
    for i in keywords:
        p.apply_async(getImgByWord, args=(i,))
    print('Waiting for all subprocesses done...')
    p.close()
    p.join()
    print('All subprocesses done.')
