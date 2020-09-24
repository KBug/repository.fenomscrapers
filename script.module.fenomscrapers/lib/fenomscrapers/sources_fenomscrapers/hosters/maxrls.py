# -*- coding: UTF-8 -*-
# modified by Venom for Fenomscrapers  (updated 9-20-2020)

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

from fenomscrapers.modules import cfscrape
from fenomscrapers.modules import cleantitle
from fenomscrapers.modules import client
from fenomscrapers.modules import source_utils
from fenomscrapers.modules import workers


class source:
	def __init__(self):
		self.priority = 28
		self.language = ['en']
		self.domains = ['max-rls.com']
		self.base_link = 'http://max-rls.com'
		self.search_link = '/?s=%s&submit=Find'


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
		self.sources = []
		try:
			self.scraper = cfscrape.create_scraper(delay=5)
			if not url: return self.sources

			self.hostDict = hostDict

			data = parse_qs(url)
			data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

			self.title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
			self.title = self.title.replace('&', 'and').replace('Special Victims Unit', 'SVU')
			self.aliases = data['aliases']

			self.episode_title = data['title'] if 'tvshowtitle' in data else None
			self.hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else data['year']
			self.year = data['year']

			query = '%s %s' % (self.title, self.hdlr)
			query = re.sub('[^A-Za-z0-9\s\.-]+', '', query)

			url = self.search_link % quote_plus(query)
			url = urljoin(self.base_link, url).replace('%3A+', '+')
			# log_utils.log('url = %s' % url, log_utils.LOGDEBUG)
			try:
				result = self.scraper.get(url).content
				links = client.parseDOM(result, "h2", attrs={"class": "postTitle"})
				threads = []
				for link in links:
					threads.append(workers.Thread(self.get_sources, link))
				[i.start() for i in threads]
				[i.join() for i in threads]
				return self.sources
			except:
				source_utils.scraper_error('MAXRLS')
				return self.sources
		except:
			source_utils.scraper_error('MAXRLS')
			return self.sources


	def get_sources(self, link):
		items = []
		try:
			url = client.parseDOM(link, 'a', ret='href')[0]
			name = client.parseDOM(link, 'a', ret='title')[0].replace('Permalink to ', '')
			if source_utils.remove_lang(name, self.episode_title):
				return
			if not source_utils.check_title(self.title, self.aliases, name, self.hdlr, self.year):
				return
			# check year for reboot/remake show issues if year is available-crap shoot
			items.append(url)
		except:
			source_utils.scraper_error('MAXRLS')
			pass

		for item in items:
			try:
				r = self.scraper.get(str(item)).content
				u = client.parseDOM(r, "div", attrs={"class": "postContent"})
				links = zip(re.findall('Download: (.*?)</strong>', u[0], re.DOTALL), re.findall('((?:\d+\,\d+\.\d+|\d+\.\d+|\d+\,\d+|\d+)\s*(?:GiB|MiB|GB|MB|gb|mb))', u[0], re.DOTALL))
				for link in links:
					urls = link[0]
					results = re.compile('href="(.+?)"', re.DOTALL).findall(urls)
					for url in results:
						if url in str(self.sources): return

						quality, info = source_utils.get_release_quality(url)
						try:
							dsize, isize = source_utils._size(link[1])
							info.insert(0, isize)
						except:
							dsize = 0
							pass
						info = ' | '.join(info)

						valid, host = source_utils.is_host_valid(url, self.hostDict)
						if not valid:
							continue
						self.sources.append({'source': host, 'quality': quality, 'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize})
			except:
				source_utils.scraper_error('MAXRLS')
				pass


	def resolve(self, url):
		return url