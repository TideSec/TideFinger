#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 18/4/15 上午2:07
# @Author  : 重剑无锋
# @Email   : TideSecPlus@gmail.com


import random,os,mysql.connector
import urllib2,re,requests
import time,hashlib,urllib

import sys

mysql_config = {
    'host': '127.0.0.1',
    # 'host': '192.168.1.201',
    'port': 3306,
    'db_name': 'finger',
    'username': 'root',
    'password': '123456'
}
def url_protocol(url):
    domain = re.findall(r'.*(?=://)', url)
    if domain:
        return domain[0]
    else:
        return url


def get_domain(target):
    try:
        url = target
        if url[0:4] == 'http':
            proto, rest = urllib.splittype(url)
            host, rest = urllib.splithost(rest)
            if host[0:3] == 'www':
                host = host[4:]
        elif url[0:3] == 'www':
            host = url[4:]
        else:
            host = url
        if ':' in host:
            host = host.split(':')[0]
        if '/' in host:
            host = host.split('/')[0]

        return host
    except:
        return target

def get_main_domain(domain):
    double_exts = ['.com.cn','.edu.cn','.gov.cn','.org.cn','.net.cn']

    main_domain = domain

    for ext in double_exts:
        if ext in domain:
            if len(domain.split('.')) > 3:
                # print "yuanshi",domain
                domain_split = domain.split('.')
                domain_new = "%s.%s.%s" % (domain_split[-3], domain_split[-2], domain_split[-1])
                # print "exact",domain
                main_domain = domain_new
            else:
                main_domain = domain

            break
        else:
            if len(domain.split('.')) > 2:
                domain_split = domain.split('.')
                domain_new = "%s.%s" % (domain_split[-2], domain_split[-1])
                main_domain = domain_new
            else:
                main_domain = domain
    return main_domain

def requests_headers():
    '''
    Random UA  for every requests && Use cookie to scan
    '''
    user_agent = ['Mozilla/5.0 (Windows; U; Win98; en-US; rv:1.8.1) Gecko/20061010 Firefox/2.0',
    'Mozilla/5.0 (Windows; U; Windows NT 5.0; en-US) AppleWebKit/532.0 (KHTML, like Gecko) Chrome/3.0.195.6 Safari/532.0',
    'Mozilla/5.0 (Windows; U; Windows NT 5.1 ; x64; en-US; rv:1.9.1b2pre) Gecko/20081026 Firefox/3.1b2pre',
    'Opera/10.60 (Windows NT 5.1; U; zh-cn) Presto/2.6.30 Version/10.60','Opera/8.01 (J2ME/MIDP; Opera Mini/2.0.4062; en; U; ssr)',
    'Mozilla/5.0 (Windows; U; Windows NT 5.1; ; rv:1.9.0.14) Gecko/2009082707 Firefox/3.0.14',
    'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36',
    'Mozilla/5.0 (Windows; U; Windows NT 6.0; fr; rv:1.9.2.4) Gecko/20100523 Firefox/3.6.4 ( .NET CLR 3.5.30729)',
    'Mozilla/5.0 (Windows; U; Windows NT 6.0; fr-FR) AppleWebKit/528.16 (KHTML, like Gecko) Version/4.0 Safari/528.16',
    'Mozilla/5.0 (Windows; U; Windows NT 6.0; fr-FR) AppleWebKit/533.18.1 (KHTML, like Gecko) Version/5.0.2 Safari/533.18.5']
    UA = random.choice(user_agent)
    headers = {
    'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'User-Agent':UA,'Upgrade-Insecure-Requests':'1','Connection':'keep-alive','Cache-Control':'max-age=0',
    'Accept-Encoding':'gzip, deflate, sdch','Accept-Language':'zh-CN,zh;q=0.8',
    "Referer": "http://www.baidu.com/link?url=www.so.com&url=www.soso.com&&url=www.sogou.com"}
    return headers


excludeext = ['.png', '.ico', '.gif','.svg', '.jpeg','js','css','xml','txt']

def getPageLinks(url):

    try:
        headers = requests_headers()

        content = requests.get(url, timeout=5, headers=headers, verify=False).text.encode('utf-8')
        links = []
        tags = ['a', 'A', 'link', 'script', 'area', 'iframe', 'form']  # img
        tos = ['href', 'src', 'action']
        if url[-1:] == '/':
            url = url[:-1]
        try:
            for tag in tags:
                for to in tos:
                    link1 = re.findall(r'<%s.*?%s="(.*?)"' % (tag, to), str(content))
                    link2 = re.findall(r'<%s.*?%s=\'(.*?)\'' % (tag, to), str(content))
                    for i in link1:
                        links.append(i)

                    for i in link2:
                        if i not in links:
                            links.append(i)

        except Exception, e:
            print e
            print '[!] Get link error'
            pass
        return links
    except:
        return []

def getMD5(c):
    m = hashlib.md5()
    m.update(c)
    psw = m.hexdigest()
    return psw

def request_url(url):
    try:

        headers={
            'User-Agent':'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:59.0) Gecko/20100101 Firefox/59.0'
        }

        r = requests.get(url=url, headers=requests_headers(),timeout=5,verify=False,)
        r.encoding = 'utf-8'
        if r.status_code==200:
            return r.content
        else:
            return ''
    except Exception,e:
        # print e
        return ''

def update_mysql(conn,url,filename,md5):
    try:
        cur=conn.cursor()
        sql = "select * from file_md5 where md5 = '"+str(md5)+"'"
        print sql
        cur.execute(sql)
        exist_md5 = cur.fetchone()
        if exist_md5:
            url = exist_md5[2]+','+url
            hint  = exist_md5[3]+1
            sql = "update file_md5 set url = '%s',hint='%s' where md5 = '%s'" % (url,hint,md5)
        else:
            sql = "INSERT INTO  file_md5 (url,filename,md5,hint) VALUES ('%s','%s','%s','%s')" % (url,filename,md5,1)
        print sql
        cur.execute(sql)
        conn.commit()
    except Exception,e:
        print e
        pass

conn=mysql.connector.connect(user=mysql_config['username'],password=mysql_config['password'],host=mysql_config['host'],database=mysql_config['db_name'],charset='utf8')

# url = 'http://www.sddlr.gov.cn/'
for url in open('url.txt','r').readlines():
    url= url.strip()
    print url
    urlprotocol = url_protocol(url)
    domain_url = get_domain(url)
    pageLinks = getPageLinks(url)
    print pageLinks
    true_url =[]
    for suburl in pageLinks:
        for ext in excludeext:
            if ext in suburl[-4:]:
                # print ext,'  ',suburl

                if re.findall(r'/', suburl):
                    if re.findall(r':', suburl):
                        true_url.append(suburl)
                    else:
                        true_url.append(urlprotocol + '://' + domain_url + '/' + suburl)
                else:
                    true_url.append(urlprotocol + '://' + domain_url + '/' + suburl)

    url_tmp1 = set(list(true_url))
    print "原长度: ",len(url_tmp1)

    url_tmp2 = []
    for x in url_tmp1:
        url_tmp2.append(x)
    print "去重后: ",len(url_tmp2)

    for url_tmp in url_tmp2:
        url_content = request_url(url_tmp)
        filename = os.path.basename(url_tmp)
        md5 =getMD5(url_content)
        print url_tmp,' ',filename,md5
        update_mysql(conn,url_tmp,filename,md5)
