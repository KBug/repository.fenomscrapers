# -*- coding: utf-8 -*-
# modified by Venom for Fenomscrapers (updated 12-23-2020)
'''
	Fenomscrapers Project
'''

import re

try: from urlparse import parse_qs, urljoin
except ImportError: from urllib.parse import parse_qs, urljoin
try: from urllib import urlencode, quote_plus, unquote, unquote_plus
except ImportError: from urllib.parse import urlencode, quote_plus, unquote, unquote_plus

from fenomscrapers.modules import client
from fenomscrapers.modules import source_utils
from fenomscrapers.modules import workers


class source:
	def __init__(self):
		self.priority = 1
		self.language = ['en']
		self.domains = ['eztv.re', 'eztv.ag', 'eztv.it', 'eztv.ch']
		self.base_link = 'https://eztv.re'
		# eztv has api but it sucks. Site query returns more results vs. api (eztv db seems to be missing the imdb_id for many so they are dopped)
		self.search_link = '/search/%s'
		self.min_seeders = 0
		self.pack_capable = False


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
		if not url: return sources
		try:
			data = parse_qs(url)
			data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

			title = data['tvshowtitle'].replace('&', 'and').replace('Special Victims Unit', 'SVU')
			aliases = data['aliases']
			episode_title = data['title']
			hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode']))
			year = data['year']

			query = '%s %s' % (title, hdlr)
			# query = re.sub(r'[^A-Za-z0-9\s\.-]+', '', query) #eztv has issues with dashes in titles
			query = re.sub(r'[^A-Za-z0-9\s\.]+', '', query)
			url = self.search_link % (quote_plus(query).replace('+', '-'))
			url = urljoin(self.base_link, url)
			# log_utils.log('url = %s' % url, log_utils.LOGDEBUG)
			html = client.request(url)

			try:
				tables = client.parseDOM(html, 'table', attrs={'class': 'forum_header_border'})
				for table in tables:
					if 'magnet:' not in table: continue
					else: break
			except:
				source_utils.scraper_error('EZTV')
				return sources

			rows = re.findall(r'<tr name="hover" class="forum_header_border">(.+?)</tr>', table, re.DOTALL)
			if not rows: return sources
		except:
			source_utils.scraper_error('EZTV')
			return sources

		for row in rows:
			try:
				try:
					columns = re.findall(r'<td\s.+?>(.+?)</td>', row, re.DOTALL)
					link = re.findall(r'href="(magnet:.+?)".*title="(.+?)"', columns[2], re.DOTALL)[0]
				except: continue

				url = str(client.replaceHTMLCodes(link[0]).split('&tr')[0])
				try: url = unquote(url).decode('utf8')
				except: pass
				hash = re.compile(r'btih:(.*?)&').findall(url)[0]

				name = link[1].split(' [eztv]')[0].split(' Torrent:')[0]
				name = source_utils.clean_name(name)
				if not source_utils.check_title(title, aliases, name, hdlr, year): continue
				name_info = source_utils.info_from_name(name, title, year, hdlr, episode_title)
				if source_utils.remove_lang(name_info): continue

				try:
					seeders = int(re.findall(r'<font color=".+?">(\d+|\d+\,\d+)</font>', columns[5], re.DOTALL)[0].replace(',', ''))
					if self.min_seeders > seeders: continue
				except:
					seeders = 0

				quality, info = source_utils.get_release_quality(name_info, url)
				try:
					size = re.findall(r'((?:\d+\,\d+\.\d+|\d+\.\d+|\d+\,\d+|\d+)\s*(?:GB|GiB|Gb|MB|MiB|Mb))', columns[3])[-1]
					dsize, isize = source_utils._size(size)
					info.insert(0, isize)
				except:
					dsize = 0
				info = ' | '.join(info)

				sources.append({'provider': 'eztv', 'source': 'torrent', 'seeders': seeders, 'hash': hash, 'name': name, 'name_info': name_info, 'quality': quality,
											'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize})
			except:
				source_utils.scraper_error('EZTV')
				continue
		return sources


	def resolve(self, url):
		return url