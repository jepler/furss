# Purpose

Fix Up RSS (and atom) fixes rss feeds without full text.

It works by taking a feed URL and an XPATH expression to extract the full
text.  For each article in the feed, it fetches the pointed-to article,
does the XPATH extraction, and packages the result as the new feed.

# Requirements

- feedparser (tested with 5.1.2)
- BeautifulSoup3 (tested with 3.2.1)
