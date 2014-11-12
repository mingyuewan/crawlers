#!/usr/bin/env python

from mechanize import Browser
from lxml import etree, html

import os
import random
import re
import sys
import time
import urllib
import uuid

from klib import ccc

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:33.0) Gecko/20100101 Firefox/33.0'
SWF_REFERER = 'http://imgcache.qq.com/tencentvideo_v1/player/TencentPlayer.swf?max_age=86400&v=20140917'
PLAYER_PLATFORM = 11
PLAYER_VERSION = '3.2.18.285'
KLIB_VERSION = '2.0'

def get_url(browser, page_url, working_dir=None):
    page_data = None
    if working_dir:
        filehash = md5(page_url)
        page_file = os.path.join(working_dir, filehash)
        if os.path.exists(page_file):
            page_data = open(page_file, 'rb').read()
    if not page_data:
        resp = browser.open(page_url)
        page_data = resp.read()
        if working_dir:
            open(page_file, 'wb').write(page_data)
    return html.fromstring(page_data)

def to_dict(json_object):
    class global_dict(dict):
        def __getitem__(self, key):
            return key
    return eval(json_object, global_dict())

def load_key(browser):
    url = 'http://vv.video.qq.com/checktime'
    resp = browser.open(url)
    xml = etree.fromstring(resp.read())
    t = int(xml.xpath('/root/t/text()')[0])

    return ccc(PLAYER_PLATFORM, PLAYER_VERSION, t)

def get_user_agent(vid, fmt):
    ua = 'Mozilla/5.0 TencentPlayerVod_1.1.91 tencent_-%s-%s' % (vid, fmt)
    return ua

def get_from(url):
    return 'v1001'

def download_movie(vid, url, fmt, fmt_name, type_name, level, br, sp, vkey):
    browser = Browser()
    browser.set_handle_robots(False)
    user_agent = 'Mozilla/5.0 TencentPlayerVod_1.1.91 tencent_-%s-%s' % (vid, fmt)

    form = {
        'stdfrom': get_from(url),
        'type': type_name,
        'vkey': vkey,
        'level': level,
        'platform': PLAYER_PLATFORM,
        'br': br,
        'fmt': fmt_name,
        'sp': sp,
    }

    query_string = urllib.urlencode(form)
    browser.addheaers = [
        ('User-Agent', user_agent),
        ('x-flash-version', 'MAC 15,0,0,189')]

    # print query_string
    resp = browser.open('%s?%s' % (url, query_string))
    of = open('t', 'wb')
    while True:
        data = resp.read(1024)
        if not data:
            break
        of.write(data)

def get_videoinfo(browser, vid):
    browser.addheaders = [('User-Agent', USER_AGENT), ('Referer', SWF_REFERER)]
    player_pid = uuid.uuid4().hex.upper()
    params = {
        'vids': vid,
        'vid': vid,
        'otype': 'xml',
        'defnpayver': 1,
        'platform': PLAYER_PLATFORM,
        'charge': 0,
        'ran': random.random(),
        'speed': random.randint(2048, 8096),
        'pid': player_pid,
        'appver': PLAYER_VERSION,
        'fhdswitch': 0,
        'fp2p': 1,
        'utype': 0,
        'cKey': load_key(browser),
        'encryptVer': KLIB_VERSION,
    }

    form = urllib.urlencode(params)
    resp = browser.open('http://vv.video.qq.com/getvinfo', data=form)
    vinfo = resp.read()
    # print vinfo
    tree = etree.fromstring(vinfo)

    fmt_id = None
    fmt_name = None
    for fmt in tree.xpath('/root/fl/fi'):
        sl = int(fmt.xpath('sl/text()')[0])
        if sl:
            fmt_id = fmt.xpath('id/text()')[0]
            fmt_name = fmt.xpath('name/text()')[0]

    assert fmt_id and fmt_name

    filename = tree.xpath('/root/vl/vi/fn/text()')[0]
    fclip = tree.xpath('/root/vl/vi/fclip/text()')[0]
    fs = tree.xpath('/root/vl/vi/fs/text()')[0]

    fps = os.path.splitext(filename)
    filename = '%s.%s%s' % (fps[0], fclip, fps[1])
    print 'File name:', filename
    print 'File size: %s (%s)' % (fs, fmt_name)

    video = tree.xpath('/root/vl/vi/ul/ui')[0]
    video_url = video.xpath('url/text()')[0]
    vt = video.xpath('vt/text()')[0]
    print video_url
    params = {
        'vid': vid,
        'otype': 'xml',
        'platform': PLAYER_PLATFORM,
        'format': fmt_id,
        'charge': 0,
        'ran': random.random(),
        'filename': filename,
        'vt': vt,
        'appver': PLAYER_VERSION,
        'cKey': load_key(browser),
        'encryptVer': KLIB_VERSION,
    }
    form = urllib.urlencode(params)
    resp = browser.open('http://vv.video.qq.com/getvkey', data=form)
    vkey_body = resp.read()
    tree = etree.fromstring(vkey_body)
    vkey = tree.xpath('/root/key/text()')[0]
    level = tree.xpath('/root/level/text()')[0]
    sr = tree.xpath('/root/sr/text()')[0]
    br = tree.xpath('/root/br/text()')[0]
    type_name = os.path.splitext(filename)[1][1:]
    video_url = '%s%s' % (video_url, filename)

    download_movie(vid, video_url, fmt_id, fmt_name, type_name, level, br, sr, vkey)

def get_suburl(browser, page_url, target_dir):
    print 'GET', page_url
    page = get_url(browser, page_url)
    scripts = page.xpath('/html/head/script')
    for script in scripts:
        if not script.text:
            continue
        if -1 != script.text.find('VIDEO_INFO'):
            break
    match = re.search('var\s+COVER_INFO\s?=\s?({[^;]+);', script.text)
    cover_info = to_dict(match.group(1))
    match = re.search('var\s+VIDEO_INFO\s?=\s?({[^;]+);', script.text)
    video_info = to_dict(match.group(1))
    match = re.search('var\s+COVER_EX_INFO\s?=\s?({[^;]+);', script.text)
    cover_ex_info = to_dict(match.group(1))
    match = re.search('var\s+LANG_INFO\s?=\s?({[^;]+);', script.text)
    lang_info = to_dict(match.group(1))
    print video_info['title']
    print 'Length:', video_info['duration']
    get_videoinfo(browser, video_info['vid'])

def txsp(page_url, target_dir):
    browser = Browser()
    browser.set_handle_robots(False)
    browser.addheaders = [('User-Agent', USER_AGENT)]
    get_suburl(browser, page_url, target_dir)

if __name__ == '__main__':
    page_url = sys.argv[1]
    target_dir = sys.argv[2]
    txsp(page_url, target_dir)
