# -*- coding: utf-8 -*-
# created by Venom for Fenomscrapers (updated 9-20-2020)

'''
    Fenomscrapers Project
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import re

try: from urlparse import parse_qs, urljoin
except ImportError: from urllib.parse import parse_qs, urljoin
try: from urllib import urlencode, quote_plus
except ImportError: from urllib.parse import urlencode, quote_plus

from fenomscrapers.modules import cleantitle
from fenomscrapers.modules import client
from fenomscrapers.modules import source_utils


class source:
	def __init__(self):
		self.priority = 25
		self.language = ['en']
		self.domains = ['2ddl.ms']
		self.base_link = 'https://2ddl.ms'
		self.search_link = '/?q=%s'


	def movie(self, imdb, title, aliases, year):
		try:
			url = {'imdb': imdb, 'title': title, 'aliases': aliases, 'year': year}
			url = urlencode(url)
			return url
		except:
			return


	def tvshow(self, imdb, tvdb, tvshowtitle, aliases, year):
		try:
			url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'aliases': aliases, 'year': year}
			url = urlencode(url)
			return url
		except:
			return


	def episode(self, url, imdb, tvdb, title, premiered, season, episode):
		try:
			if not url: return
			url = parse_qs(url)
			url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
			url['title'], url['premiered'], url['season'], url['episode'] = title, premiered, season, episode
			url = urlencode(url)
			return url
		except:
			return


	def sources(self, url, hostDict):
		sources = []
		try:
			if not url: return sources
			data = parse_qs(url)
			data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

			title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
			title = title.replace('&', 'and').replace('Special Victims Unit', 'SVU')
			year = data['year']

			hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else year

			query = '%s %s' % (title, hdlr)
			query = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', '', query)

			url = self.search_link % quote_plus(query)
			url = urljoin(self.base_link, url).replace('+', '-')

			if 'tvshowtitle' in data: # shows with year check
				query = '%s %s %s' % (title, year, hdlr)
				query = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', '', query)
				url = self.search_link % quote_plus(query)
				url = urljoin(self.base_link, url).replace('+', '-')
				# log_utils.log('url = %s' % url, __name__, log_utils.LOGDEBUG)
				r = client.request(url)
				posts = client.parseDOM(r, "p", attrs={"class": "download-link"})

				if not posts: # seasons check
					query = '%s S%02d' % (title, int(data['season']))
					query = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', '', query)
					url = self.search_link % quote_plus(query)
					url = urljoin(self.base_link, url).replace('+', '-')
					# log_utils.log('url = %s' % url, __name__, log_utils.LOGDEBUG)
					r = client.request(url)
					posts = client.parseDOM(r, "p", attrs={"class": "download-link"})
			else:
				# log_utils.log('url = %s' % url, __name__, log_utils.LOGDEBUG)
				r = client.request(url)
				posts = client.parseDOM(r, "p", attrs={"class": "download-link"})
			if not posts:
				return sources
		except:
			source_utils.scraper_error('2DDL')
			return sources

		items = []
		for post in posts:
			try:
				u = client.parseDOM(post, 'a', ret='href')[0]
				name1 = u.split('https://2ddl.ms/')[1].rstrip('/')
				name1 = re.sub('[^A-Za-z0-9]+', '.', name1)

				r = client.request(u)
				u = client.parseDOM(r, "div", attrs={"class": "single-link"})
				for t in u:
					r = client.parseDOM(t, 'a', ret='href')
					for url in r:
						if any(x in url for x in ['.rar', '.zip', '.iso', '.sample.']):
							continue
						valid, host = source_utils.is_host_valid(url, hostDict)
						if valid:
							if 'OnceDDL_' in url:
								name = url.split('OnceDDL_')[1]
								name = re.sub('[^A-Za-z0-9]+', '.', name).upper()
							else:
								name = name1.upper()
							if source_utils.remove_lang(name):
								continue
							t = name.split(hdlr)[0].replace(data['year'], '').replace('(', '').replace(')', '').replace('&', 'and')
							if cleantitle.get(t) != cleantitle.get(title):
								continue
							if hdlr not in name:
								continue
							if url in str(sources):
								continue
							quality, info = source_utils.get_release_quality(name, url)
							# size info not available on 2ddl
							dsize = 0
							sources.append({'source': host, 'quality': quality, 'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize})
			except:
				source_utils.scraper_error('2DDL')
				pass
		return sources


	def resolve(self, url):
		return url