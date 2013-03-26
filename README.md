# Purpose

Fix Up RSS (and atom) fixes rss feeds without full text.

It works by taking a feed URL and one or more XPATH expressions to extract the
full text.  For each article in the feed, it fetches the pointed-to article,
does the XPATH extractions, and packages the result as the new feed.

# Requirements

- Python 2.7 (2.6 is missing some xpath features such as attribute matching)
- feedparser (tested with 5.1.2)
- BeautifulSoup3 (tested with 3.2.1)

Optional:
- memcached (the default debian/ubuntu packaging sets up memcached compatibly)

# Configuration

furss is configured via an rc file (really, a Python script), either
`~/.furssrc` or the file named on the commandline.  The defaults are shown near
the top of the `furss.py` script.  `furssrc.sample` shows a sample
configuration.

# License

The following license is granted by the authors for all code in this
repository:

> This program is free software; you can redistribute it and/or modify
> it under the terms of the GNU General Public License as published by
> the Free Software Foundation; either version 2 of the License, or
> (at your option) any later version.
>
> This program is distributed in the hope that it will be useful,
> but WITHOUT ANY WARRANTY; without even the implied warranty of
> MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
> GNU General Public License for more details.
>
> You should have received a copy of the GNU General Public License
> along with this program; if not, write to the Free Software
> Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

Individual files may also offer more liberal licenses.
