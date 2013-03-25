#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#    Copyright © 2013 Jeff Epler <jepler@unpythonic.net>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import BeautifulSoup
import StringIO
import feedparser
import robotparser
import sys
import time
import urllib
import urlparse
import xml.etree.ElementTree


useragent = "Feed-Fixer/0.1 (python)"
expiry = 3600

class CacherInterface:
    def get(self, k, f):
        """Retrieve k from the underlying cache.  If not present, call f and
        use its return value as the value (or, if f is None, return None).
        Keys must be strings or tuples of strings; values must be pickleable
        (though some derived classes may have looser requirements)"""

        raise NotImplemented

    def set(self, k, v):
        """Store v in the underlying cache at address k.  Must obey the same
        rules as get()."""

        raise NotImplemented

class SimpleCacher(CacherInterface):
    """A simple cacher which always memory-caches; the cache grows forever"""
    def __init__(self):
        self.d = {}

    def get(self, k, f, *args):
        print >>sys.stderr, "get", k
        if k not in self.d:
            if f is None:
                print >>sys.stderr, "-> None"
                return None
            else:
                print >>sys.stderr, "f()"
                self.d[k] = f(*args)
        print >>sys.stderr, "->", self.d[k]
        return self.d[k]

    def set(self, k, v):
        print >>sys.stderr, "set", k
        self.d[k] = v

cache = SimpleCacher()

class Opener(urllib.FancyURLopener):
    version = useragent

    def http_error_304(self, url, fp, errcode, errmsg, headers, data=None):
        return urllib.addinfourl(fp, headers, url, errcode)

def urlopen_with_etag(u, e=None):
    o = Opener()
    if e is not None:
        o.addheader('If-None-Match', e)
    return o.open(u)

def cached(f):
    kb = (f.__module__, f.__name__)
    def inner(*args):
        return cache.get(kb + args, f, *args)
    return inner

@cached
def get_robot(ru):
    return robotparser.RobotFileParser(ru)

@cached
def robot_ok(u):
    parsed = urlparse.urlsplit(u)
    if parsed.scheme not in ('http', 'https'): return 0
    ru = "%s://%s/robots.txt" % (parsed.scheme, parsed.netloc)
    return get_robot(ru).can_fetch(useragent, u)
    
def is_tracker(k):
    return k.startswith("utm_")

def filter_trackers(query):
    filtered = [i for i in urlparse.parse_qsl(query) if not is_tracker(i[0])]
    urllib.urlencode(filtered, True)

def remove_trackers(url):
    parsed = urlparse.urlsplit(url)
    fixed = (parsed[0], parsed[1], parsed[2], filter_trackers(parsed[3]), parsed[4])
    return urlparse.urlunsplit(fixed) 

def get_url(u):
    if not robot_ok(u): return None
    data = cache.get(('get_url', u), None)
    if data is not None:
        u = data[0]
        old_etag = data[1]
        old_fetch_time = data[2]
        if old_fetch_time + expiry < time.time(): return data[3]

    f = urllib.urlopen(u)
    if f.code == 304:
        return data[0], data[3]
    else:
        etag = f.headers.getheader('etag', None)
        res = f.read()
        now = time.time()
        cache.set(('get_url', u), (f.url, etag, now, res, f.headers))
        cache.set(('get_url', f.url), (f.url, etag, now, res, f.headers))
        return f.url, res

    
def bsparse(text):
    soup = BeautifulSoup.BeautifulSoup(text,
            convertEntities=BeautifulSoup.BeautifulSoup.HTML_ENTITIES)
    def emit(soup):
        if isinstance(soup, BeautifulSoup.NavigableString):
            if isinstance(soup, BeautifulSoup.Comment):
                return
            builder.data(soup)
        else:
            builder.start(soup.name, dict(soup.attrs))
            for s in soup:
                emit(s)
            builder.end(soup.name)
    builder = xml.etree.ElementTree.TreeBuilder()
    emit(soup)
    doc = builder.close()
    if len(doc) == 1: return doc[0]
    doc.tag = 'html'
    return doc

def do_extract(doc, query):
    result = []
    for q in query:
        result.extend(doc.findall(q))
    if len(result) == 1:
        return result[0]
    e = xml.etree.ElementTree.Element('div')
    e._children = result
    return e
 
class FeedFixer:
    def __init__(self, feed, get_body):
        self.get_body = get_body
        feed = get_url(feed)
        s = StringIO.StringIO(feed[1])
        s.url = feed[0]
        self.parsed = feedparser.parse(s)

    def doit(self, entry):
        result = {}
        for k in ('title', 'link', 'description', 'published', 'id'):
            if k in entry: result[k] = entry[k]
        if 'link' in result:
            link = result['link']
            u = get_url(link)
            soup = bsparse(u[1])
            result['newcontent'] = do_extract(soup, self.get_body)
            result['link'] = remove_trackers(u[0])
        return result

    def get(self, k, default=None):
        return getattr(self.parsed, k, default)

    def __iter__(self):
        for entry in self.parsed.entries:
            yield self.doit(entry)

def firstn(it, lim):
    if not lim:
        for i in it: yield i
    else:
        for i, j in enumerate(it):
            if i == lim: break
            yield j

def main(feed, get_body, lim=None):
    f = FeedFixer(feed, get_body)

    builder = xml.etree.ElementTree.TreeBuilder()
    def start(t, **kw):
        builder.start(t, kw)
    def end(t):
        builder.end(t)
    def tag(t, _data=None, **kw):
        builder.start(t, kw)
        if _data: builder.data(_data)
        builder.end(t)

    start('feed', xmlns='http://www.w3.org/2005/Atom')
    if 'title' in f.parsed: tag('title', f.parsed['title'])
    if 'link' in f.parsed: tag('link', f.parsed['link'])
    if 'id' in f.parsed: tag('id', f.parsed['id'])
    for a in f.get('author', []):
        start('author')
        if 'name' in a: tag('name', a['name'])
        if 'email' in a: tag('email', a['email'])
        if 'uri' in a: tag('uri', a['uri'])
        end('author')

    for e in firstn(f, lim):
        start('entry')
        if 'title' in e: tag('title', e['title'])
        if 'link' in e: tag('link', e['link'])
        if 'id' in e: tag('id', e['id'])
        if 'summary' in e: tag('summary', e['summary'])
        if 'updated' in e: tag('updated', e['updated'])
        tag('content', xml.etree.ElementTree.tostring(e['newcontent']), type='html', **{'xml:base': e['link']})
        end('entry')
    end('feed')
    return xml.etree.ElementTree.tostring(builder.close())

print main('http://emergent.unpythonic.net/_atom', ['.//*[@class="content"]'])
#print main('http://rss.slashdot.org/Slashdot/slashdot', ['.//article/header', './/article/div[@class="body"]'], 3)
