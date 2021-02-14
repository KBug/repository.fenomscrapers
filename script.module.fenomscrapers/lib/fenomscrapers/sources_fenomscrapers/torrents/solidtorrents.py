# -*- coding: utf-8 -*-
# created by Venom for Fenomscrapers (updated 1-09-2021)
'''
	Fenomscrapers Project
'''

from json import loads as jsloads
import re
try: #Py2
	from urlparse import parse_qs, urljoin
	from urllib import urlencode, quote_plus, unquote_plus
except ImportError: #Py3
	from urllib.parse import parse_qs, urljoin, urlencode, quote_plus, unquote_plus

from fenomscrapers.modules import client
from fenomscrapers.modules import source_utils
from fenomscrapers.modules import workers


class source:
	def __init__(self):
		self.priority = 1
		self.language = ['en']
		self.domains = ['solidtorrents.net']
		self.base_link = 'https://solidtorrents.net'
		self.search_link = '/api/v1/search?q=%s&category=all&sort=size'
		self.min_seeders = 0
		self.pack_capable = True


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
		if not url: return self.sources
		try:
			data = parse_qs(url)
			data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

			self.title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
			self.title = self.title.replace('&', 'and').replace('Special Victims Unit', 'SVU')
			self.aliases = data['aliases']
			self.episode_title = data['title'] if 'tvshowtitle' in data else None
			self.year = data['year']
			self.hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else self.year

			query = '%s %s' % (self.title, self.hdlr)
			query = re.sub(r'[^A-Za-z0-9\s\.-]+', '', query)
			urls = []
			url = self.search_link % quote_plus(query)
			url = urljoin(self.base_link, url)
			urls.append(url)
			urls.append(url + '&skip=20')
			urls.append(url + '&skip=40')
			urls.append(url + '&skip=60')
			urls.append(url + '&skip=80')
			# log_utils.log('urls = %s' % urls, log_utils.LOGDEBUG)

			threads = []
			for url in urls:
				threads.append(workers.Thread(self.get_sources, url))
			[i.start() for i in threads]
			[i.join() for i in threads]
			return self.sources
		except:
			source_utils.scraper_error('SOLIDTORRENTS')
			return self.sources


	def get_sources(self, url):
		try:
			r = client.request(url, timeout='5')
			if not r: return
			r = jsloads(r)
			results = r['results']

			for item in results:
				try:
					url = unquote_plus(item['magnet']).replace(' ', '.')
					url = re.sub(r'(&tr=.+)&dn=', '&dn=', url) # some links on solidtorrents &tr= before &dn=
					url = source_utils.strip_non_ascii_and_unprintable(url)
					hash = item['infohash'].lower()
					if len(hash) != 40: continue
					if url in str(self.sources): continue

					name = item['title']
					name = source_utils.clean_name(name)
					if not source_utils.check_title(self.title, self.aliases, name, self.hdlr, self.year): continue
					name_info = source_utils.info_from_name(name, self.title, self.year, self.hdlr, self.episode_title)
					if source_utils.remove_lang(name_info): continue

					if not self.episode_title: #filter for eps returned in movie query (rare but movie and show exists for Run in 2020)
						ep_strings = [r'(?:\.|\-)s\d{2}e\d{2}(?:\.|\-|$)', r'(?:\.|\-)s\d{2}(?:\.|\-|$)', r'(?:\.|\-)season(?:\.|\-)\d{1,2}(?:\.|\-|$)']
						if any(re.search(item, name.lower()) for item in ep_strings): continue

					try:
						seeders = int(item['swarm']['seeders'])
						if self.min_seeders > seeders: continue
					except:
						seeders = 0

					quality, info = source_utils.get_release_quality(name_info, url)
					try:
						dsize, isize = source_utils.convert_size(item["size"], to='GB')
						info.insert(0, isize)
					except:
						dsize = 0
					info = ' | '.join(info)

					self.sources.append({'provider': 'solidtorrents', 'source': 'torrent', 'seeders': seeders, 'hash': hash, 'name': name, 'name_info': name_info,
													'quality': quality, 'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize})
				except:
					source_utils.scraper_error('SOLIDTORRENTS')
		except:
			source_utils.scraper_error('SOLIDTORRENTS')


	def sources_packs(self, url, hostDict, search_series=False, total_seasons=None, bypass_filter=False):
		self.sources = []
		if not url: return self.sources
		try:
			self.search_series = search_series
			self.total_seasons = total_seasons
			self.bypass_filter = bypass_filter

			data = parse_qs(url)
			data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

			self.title = data['tvshowtitle'].replace('&', 'and').replace('Special Victims Unit', 'SVU')
			self.aliases = data['aliases']
			self.imdb = data['imdb']
			self.year = data['year']
			self.season_x = data['season']
			self.season_xx = self.season_x.zfill(2)

			# query = re.sub(r'(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', '', self.title)
			query = re.sub(r'[^A-Za-z0-9\s\.-]+', '', self.title)
			queries = [
						self.search_link % quote_plus(query + ' S%s' % self.season_xx),
						self.search_link % quote_plus(query + ' Season %s' % self.season_x)
							]
			if self.search_series:
				queries = [
						self.search_link % quote_plus(query + ' Season'),
						self.search_link % quote_plus(query + ' Complete')
								]

			threads = []
			for url in queries:
				link = urljoin(self.base_link, url)
				threads.append(workers.Thread(self.get_sources_packs, link))
			[i.start() for i in threads]
			[i.join() for i in threads]
			return self.sources
		except:
			source_utils.scraper_error('SOLIDTORRENTS')
			return self.sources


	def get_sources_packs(self, link):
		# log_utils.log('link = %s' % str(link), __name__, log_utils.LOGDEBUG)
		try:
			r = client.request(link, timeout='5')
			if not r: return
			r = jsloads(r)
			results = r['results']
		except:
			source_utils.scraper_error('SOLIDTORRENTS')
			return

		for item in results:
			try:
				url = unquote_plus(item['magnet']).replace(' ', '.')
				url = re.sub(r'(&tr=.+)&dn=', '&dn=', url) # some links on solidtorrents &tr= before &dn=
				url = source_utils.strip_non_ascii_and_unprintable(url)
				hash = item['infohash'].lower()
				if len(hash) != 40: continue
				if url in str(self.sources): continue

				name = item['title']
				name = source_utils.clean_name(name)
				if not self.search_series:
					if not self.bypass_filter:
						if not source_utils.filter_season_pack(self.title, self.aliases, self.year, self.season_x, name):
							continue
					package = 'season'

				elif self.search_series:
					if not self.bypass_filter:
						valid, last_season = source_utils.filter_show_pack(self.title, self.aliases, self.imdb, self.year, self.season_x, name, self.total_seasons)
						if not valid: continue
					else:
						last_season = self.total_seasons
					package = 'show'

				name_info = source_utils.info_from_name(name, self.title, self.year, season=self.season_x, pack=package)
				if source_utils.remove_lang(name_info): continue

				try:
					seeders = int(item['swarm']['seeders'])
					if self.min_seeders > seeders: continue
				except:
					seeders = 0

				quality, info = source_utils.get_release_quality(name_info, url)
				try:
					dsize, isize = source_utils.convert_size(item["size"], to='GB')
					info.insert(0, isize)
				except:
					dsize = 0
				info = ' | '.join(info)

				item = {'provider': 'solidtorrents', 'source': 'torrent', 'seeders': seeders, 'hash': hash, 'name': name, 'name_info': name_info, 'quality': quality,
							'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize, 'package': package}
				if self.search_series:
					item.update({'last_season': last_season})
				self.sources.append(item)
			except:
				source_utils.scraper_error('SOLIDTORRENTS')


	def resolve(self, url):
		return url