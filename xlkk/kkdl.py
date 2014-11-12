#!/usr/bin/env python

from mechanize import Browser
from lxml import etree, html
import hashlib
import os
import re
import random
import sys
import time

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:33.0) Gecko/20100101 Firefox/33.0'
AGENT_VER = '5050'

def md5(data):
    m = hashlib.md5()
    m.update(data)
    return m.hexdigest()

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

def random1(length):
    chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    selected = []
    while len(selected) < length:
        selected.append(chars[random.randint(0, len(chars)-1)])
    return ''.join(selected).upper()

def random2(length):
    chars = '689XL'
    selected = []
    while len(selected) < length:
        selected.append(chars[random.randint(0, len(chars)-1)])
    return ''.join(selected).upper()

def generate_referer():
    referer = 'KKVPVOD-%s-%s-%s-%s-%s%s-%s' % (AGENT_VER, random1(8), random1(4), random1(4), random2(1), random1(3), random1(12))
    return referer

def download_video(browser, video_url, target):
    size = 0
    resp = browser.open(video_url)
    while True:
        data = resp.read(4096)
        if not data:
            break
        target.write(data)
        size = size + len(data)
    return size

def download_movie(surl, video_size, target):
    referer = generate_referer()

    browser = Browser()
    browser.set_handle_robots(False)
    browser.addheaders = [('User-Agent', USER_AGENT)]

    gcid = surl.split('/')[4].upper()
    cid = surl.split('/')[5]
    cdn_url = 'http://p2s.cl.kankan.com/getCdnresource_flv?gcid=%s&bid=21' % gcid
    page = get_url(browser, cdn_url)
    scripts = page.xpath('/html/head/script')
    isp = None
    json_obj = None
    check_out_obj = None
    for script in scripts:
        for s in script.text.split('var'):
            s = s.strip()
            if s.startswith('isp'):
                match = re.match('isp\s?=\s?"([^"]+)";', s)
                isp = match.group(1)
            elif s.startswith('jsonObj'):
                match = re.match('jsonObj\s?=\s?([^$]+)', s)
                json_obj = to_dict(match.group(1))
            elif s.startswith('jsCheckOutObj'):
                match = re.match('jsCheckOutObj\s?=\s?([^$]+)', s)
                check_out_obj = to_dict(match.group(1))

    if not isp or not json_obj or not check_out_obj:
        raise Exception('Page may be updated')
    cdn = json_obj['cdnlist1'][0]

    key = md5('xl_mp43651%d%d' % (check_out_obj['param1'], check_out_obj['param2']))
    key1 = check_out_obj['param2']
    stream_url = 'http://%s:80/%s?key=%s&key1=%s' % (cdn['ip'], cdn['path'], key, key1)

    ts = int(1000*time.time())
    flash_ver = 'id=sotester&client=FLASH%20WIN%2010,0,45,2&version=6.13.60'
    stream_url = '%s&ts=%d&%s' % (stream_url, ts, flash_ver)

    print 'Save to', target
    start_time = time.time()
    if os.path.exists(target):
        download_size = os.path.getsize(target)
    else:
        download_size = 0
    of = open(target, 'wb+')
    trunk_size = 0x20000
    while download_size < video_size:
        from_pos = download_size
        to_pos = download_size + trunk_size - 1
        if to_pos >= video_size:
            to_pos = video_size - 1
        tfn = '%d-%d' % (from_pos, to_pos)
        # path = os.path.join(target_dir, tfn)
        browser.addheaders = [('User-Agent', USER_AGENT), ('Referer', referer), ('Range', 'bytes=%s' % tfn)]
        keya = md5('xl_mp43651%s%d%d%s' % (cid, from_pos, to_pos, ts))
        download_url = '%s&keya=%s&keyb=%d&ver=%s' % (stream_url, keya, ts, AGENT_VER)
        trunk_start_time = time.time()
        real_size = download_video(browser, download_url, of)
        trunk_time = time.time() - trunk_start_time
        download_size = download_size + real_size
        print '[%%%02d] %d/%d in %dKB/s\r' % (download_size*100/video_size, download_size, video_size, int((real_size/trunk_time)/1024)),
        sys.stdout.flush()
    of.close()
    end_time = time.time()
    print '\nTime:%d Speed:%dKB/s' % (int(end_time - start_time), (video_size/1024.0)/(end_time - start_time))

def get_suburl(browser, page_url, target_dir):
    print 'GET', page_url
    page = get_url(browser, page_url)
    scripts = page.xpath('/html/script')
    movie_title = None
    movie_id = None
    submovie_id = None
    for line in scripts[0].text.split('\n'):
        line = line.strip()
        match = re.match('var\s+G_MOVIEID\s?=\s?\'(\d+)\';', line)
        if match:
            movie_id = int(match.group(1))
        match = re.match('var\s+G_MOVIE_TITLE\s?=\s?\'([^\']+)\';', line)
        if match:
            movie_title = match.group(1)
        match = re.match('var\s+G_SUBMOVIEID\s?=\s?\'(\d+)\';', line)
        if match:
            submovie_id = int(match.group(1))
        if movie_id and movie_title and submovie_id:
            break
    movie_data = None
    submovie_data = None
    for line in scripts[2].text.split('\n'):
        line = line.strip()
        match = re.match('var\s+G_MOVIE_DATA\s?=\s?([^;]+);', line)
        if match:
            movie_data = to_dict(match.group(1))
        match = re.match('var\s+G_SUBMOVIE_DATA\s?=\s?([^;]+);', line)
        if match:
            submovie_data = to_dict(match.group(1))
        if movie_data and submovie_data:
            break
    if submovie_id is None or movie_data is None or submovie_data is None:
        raise Exception('Page may be updated')
#    print movie_data
    subids = movie_data['subids']
    new_movie_data = {}
    for i in range(len(subids)):
        new_movie_data[subids[i]] = {}
        for key in movie_data.keys():
            if not movie_data[key]:
                continue
            new_movie_data[subids[i]][key] = movie_data[key][i]
    surl_keys = ['sids', 'surls', 'length_r', 'size']
    for item in submovie_data:
        submovieid = item.get('submovieid')
        if not submovieid:
            continue
        sids = item['sids']
        surls = {}
        for i in range(len(sids)):
            surls[sids[i]] = {}
            for k in surl_keys:
                surls[sids[i]][k] = item[k][i]
        for k in surl_keys:
            item.pop(k)
        item['surls'] = surls
        new_movie_data[submovieid].update(item)
    submovie_data = new_movie_data.get(submovie_id)
    print movie_title, submovie_data['subnames'], submovie_data['attracts']
    print 'Length:', submovie_data['length']
    surls = submovie_data['surls'].values()
    max_size_surl = surls[0]
    print 'Avaliable Sizes:',
    for surl in surls:
        if surl['size'] == 0:
            continue
        if surl['size'] > max_size_surl['size']:
            max_size_surl = surl
        print surl['size'],
    print 

    print 'Size:', max_size_surl['size']
    extname = os.path.splitext(max_size_surl['surls'])[1]
    target_name = '%s_%s_%s%s' % (movie_id, submovie_id, max_size_surl['sids'], extname)
    target_file = os.path.join(target_dir, target_name)

    download_movie(max_size_surl['surls'], max_size_surl['size'], target_file)

def kkdl(page_url, target_dir):
    browser = Browser()
    browser.set_handle_robots(False)
    browser.addheaders = [('User-Agent', USER_AGENT)]
    get_suburl(browser, page_url, target_dir)

if __name__ == '__main__':
    page_url = sys.argv[1]
    target_dir = sys.argv[2]
    kkdl(page_url, target_dir)
