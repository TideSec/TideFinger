#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import urllib3
import hashlib
import logging
import requests
import urllib.parse
import urllib.request
from bs4 import BeautifulSoup
from webanalyzer.utils import update
from webanalyzer.condition import Condition

__all__ = ["WebAnalyzer"]

urllib3.disable_warnings()
logger = logging.getLogger(__file__)

RULES = {}
RULE_TYPES = set()
DEFAULT_RULE_DIR = os.path.join(os.getcwd(), "webanalyzer/rules")
REPOSITORY = "webanalyzer/rules"


class WebAnalyzer(object):
    def __init__(self):
        self.aggression = False
        self.url = None
        self.timeout = 30
        self.allow_redirect = True
        self.headers = {
    'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'User-Agent':'Mozilla/5.0 (Windows; U; Windows NT 6.0; fr-FR) AppleWebKit/528.16 (KHTML, like Gecko) Version/4.0 Safari/528.16',
    'Upgrade-Insecure-Requests':'1','Connection':'keep-alive','Cache-Control':'max-age=0',
    'Accept-Encoding':'gzip, deflate, sdch','Accept-Language':'zh-CN,zh;q=0.8',
    "Referer": "http://www.baidu.com/link?url=www.so.com&url=www.soso.com&&url=www.sogou.com",
    'Cookie':"PHPSESSID=gljsd5c3ei5n813roo4878q203"}

        self.rule_dir = DEFAULT_RULE_DIR

        self._targets = {}
        self._cond_parser = Condition()

    def update_rules(self) -> bool:
        return update(REPOSITORY, self.rule_dir)

    @staticmethod
    def list_rules():
        return RULES

    def reload_rules(self) -> int:
        global RULES, RULE_TYPES
        new_rules = {}
        new_rule_types = set()
        for rule_type in os.listdir(self.rule_dir):
            rule_type_dir = os.path.join(self.rule_dir, rule_type)
            if not os.path.isdir(rule_type_dir):
                continue
            new_rule_types.add(rule_type)
            for i in os.listdir(rule_type_dir):
                if not i.endswith('.json'):
                    continue

                with open(os.path.join(rule_type_dir, i)) as fd:
                    try:
                        data = json.load(fd)
                        for match in data['matches']:
                            if 'regexp' in match:
                                match['regexp'] = re.compile(match['regexp'], re.I)

                            if 'certainty' not in match:
                                match['certainty'] = 100

                        data['origin'] = rule_type
                        key = '%s_%s' % (rule_type, data['name'])
                        new_rules[key] = data
                    except Exception as e:
                        logger.error('parse %s failed, error: %s' % (i, e))

        RULES = new_rules
        RULE_TYPES = new_rule_types
        return len(RULES)

    def test_rule(self, url: str, rule_path: str) -> hash:
        if not os.path.exists(rule_path):
            logger.warning("%s does not exists, exit" % rule_path)
            return

        self.url = url
        self._request(self.url)

        with open(rule_path) as fd:
            rule = json.load(fd)

            if len(rule['matches']) == 0:
                logger.info("matches empty, return")
                return

            rule['origin'] = 'test'

            for match in rule['matches']:
                if 'regexp' in match:
                    match['regexp'] = re.compile(match['regexp'], re.I)

                if 'certainty' not in match:
                    match['certainty'] = 100

            return self._check_rule(rule)

    def _request(self, url: str) -> hash:
        try:
            rp = requests.get(url, headers=self.headers, verify=False, timeout=self.timeout,
                              allow_redirects=self.allow_redirect)
        except Exception as e:
            logger.error("request error: %s" % str(e))
            return

        script = []
        meta = {}

        p = BeautifulSoup(rp.text, "html5lib")

        for data in p.find_all("script"):
            script_src = data.get("src")
            if script_src:
                script.append(script_src)

        for data in p.find_all("meta"):
            meta_name = data.get("name")
            meta_content = data.get("content", "")
            if meta_name:
                meta[meta_name] = meta_content

        title = p.find("title")
        if title:
            title = title.text
        else:
            title = ""

        raw_headers = '\n'.join('{}: {}'.format(k, v) for k, v in rp.headers.items())
        self._targets[url] = {
            "url": url,
            "body": rp.text,
            "headers": rp.headers,
            "status": rp.status_code,
            "script": script,
            "meta": meta,
            "title": title,
            "cookies": rp.cookies,
            "raw_cookies": rp.headers.get("set-cookie", ""),
            "raw_response": raw_headers + rp.text,
            "raw_headers": raw_headers,
            "md5": hashlib.md5(rp.content).hexdigest(),
        }

        return self._targets[url]

    def _check_match(self, match: hash, aggression: bool = False) -> (bool, str):
        s = {'regexp', 'text', 'md5', 'status'}  # 如果增加新的检测方式，需要修改这里
        if not s.intersection(list(match.keys())):
            return False, None

        target = self._targets[self.url]
        if 'url' in match:
            full_url = urllib.parse.urljoin(self.url, match['url'])
            if match['url'] == '/':  # 优化处理
                pass
            elif full_url in self._targets:
                target = self._targets[full_url]
            elif aggression:
                target = self._request(full_url)
            else:
                logger.debug("match has url(%s) field, but aggression is false" % match['url'])
                return False, None

        # parse search
        search_context = target['body']
        if 'search' in match:
            if match['search'] == 'all':
                search_context = target['raw_response']
            elif match['search'] == 'headers':
                search_context = target['raw_headers']
            elif match['search'] == 'script':
                search_context = target['script']
            elif match['search'] == 'title':
                search_context = target['title']
            elif match['search'] == 'cookies':
                search_context = target['raw_cookies']
            elif match['search'].endswith(']'):
                for i in ('headers', 'meta', 'cookies'):
                    if not match['search'].startswith('%s[' % i):
                        continue

                    key = match['search'][len('%s[' % i):-1]
                    if key not in target[i]:
                        return False, None
                    search_context = target[i][key]

            match.pop('search')

        version = match.get('version', None)
        for key in list(match.keys()):
            if key == 'status':
                if match[key] != target[key]:
                    return False, None

            if key == 'md5':
                if target['md5'] != match['md5']:
                    return False, None

            if key == 'text':
                search_contexts = search_context
                if isinstance(search_context, str):
                    search_contexts = [search_context]

                for search_context in search_contexts:
                    if match[key] not in search_context:
                        continue
                    break
                else:
                    return False, None

            if key == 'regexp':
                search_contexts = search_context
                if isinstance(search_context, str):
                    search_contexts = [search_context]

                for search_context in search_contexts:
                    result = match[key].findall(search_context)
                    if not result:
                        continue

                    if 'offset' in match:
                        if isinstance(result[0], str):
                            version = result[0]
                        elif isinstance(result[0], tuple):
                            if len(result[0]) > match['offset']:
                                version = result[0][match['offset']]
                            else:
                                version = ''.join(result[0])
                    break
                else:
                    return False, None

        return True, version

    def _check_rule(self, rule: hash) -> hash:
        matches = rule['matches']

        cond_map = {}
        result = {
            'name': rule['name'],
            'origin': rule['origin']
        }

        for index, match in enumerate(matches):
            aggression = False
            if self.aggression == 2:
                aggression = True
            elif self.aggression == 1 and rule['origin'] == 'custom':
                aggression = True

            is_match, version = self._check_match(match, aggression=aggression)
            if is_match:
                cond_map[str(index)] = True
                if version:
                    result['version'] = version
            else:
                cond_map[str(index)] = False

        # default or
        if 'condition' not in rule:
            if any(cond_map.values()):
                return result
            return

        if self._cond_parser.parse(rule['condition'], cond_map):
            return result

    def start(self, url: str, reload: bool = True):
        logger.debug("process %s" % url)
        self.url = url
        results = []
        implies = set()
        excludes = set()

        if not self._request(url):
            logger.info("request %s failed" % url)
            return

        self._request(urllib.parse.urljoin(url, '/favicon.ico'))

        if reload:
            self.reload_rules()

        for name, rule in RULES.items():
            # print(name)
            r = self._check_rule(rule)
            if r:
                if 'implies' in rule:
                    if isinstance(rule['implies'], str):
                        implies.add(rule['implies'])
                    else:
                        implies.update(rule['implies'])

                if 'excludes' in rule:
                    if isinstance(rule['excludes'], str):
                        excludes.add(rule['excludes'])
                    else:
                        excludes.update(rule['excludes'])

                if r['name'] in excludes:
                    continue
                results.append(r)

        for imply in implies:
            _result = {
                'name': imply,
                "origin": 'implies'
            }

            for rule_type in RULE_TYPES:
                rule_name = '%s_%s' % (rule_type, imply)

                rule = RULES.get(rule_name)
                if not rule:
                    continue

                if 'excludes' in rule:
                    if isinstance(rule['excludes'], str):
                        excludes.add(rule['excludes'])
                    else:
                        excludes.update(rule['excludes'])

            if _result['name'] in excludes:
                continue
            results.append(_result)

        return results

def check(url, update):
    w = WebAnalyzer()
    w.rule_dir = os.path.join(os.getcwd(), "webanalyzer/rules")

    if update:
        if w.update_rules():
            print("update rules done")
        return

    w.aggression = 0

    w.allow_redirect = True

    r = w.start(url)
    # if r:
    #     click.echo(json.dumps(r, indent=4))
    banner = []
    for x in r:
        # print(x)
        if 'version' in x.keys():
            banner.append(x['name']+' '+x['version'])
        else:
            banner.append(x['name'])
    return banner
