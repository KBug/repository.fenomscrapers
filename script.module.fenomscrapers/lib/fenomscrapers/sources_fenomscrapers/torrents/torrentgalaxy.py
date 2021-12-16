# -*- coding: utf-8 -*-
# created by Venom for Fenomscrapers (updated 12-15-2021) increased timeout=7
"""
	Fenomscrapers Project
"""

import re
from urllib.parse import quote_plus, unquote_plus
from fenomscrapers.modules import cfscrape
from fenomscrapers.modules import client
from fenomscrapers.modules import source_utils
from fenomscrapers.modules import workers


class source:
	priority = 2
	pack_capable = True
	hasMovies = True
	hasEpisodes = True
	def __init__(self):
		self.language = ['en']
		self.base_link = 'https://torrentgalaxy.to'
		self.search_link = '/torrents.php?search=%s&sort=seeders&order=desc'
		self.min_seeders = 0

	def sources(self, data, hostDict):
		sources = []
		if not data: return sources
		append = sources.append
		try:
			scraper = cfscrape.create_scraper()
			title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
			title = title.replace('&', 'and').replace('Special Victims Unit', 'SVU')
			aliases = data['aliases']
			episode_title = data['title'] if 'tvshowtitle' in data else None
			year = data['year']
			hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else year

			if 'tvshowtitle' in data:
				query = '%s %s' % (title, hdlr)
				query = re.sub(r'[^A-Za-z0-9\s\.-]+', '', query)
				url = self.search_link % quote_plus(query)
			else:
				url = self.search_link % data['imdb']
			url = '%s%s' % (self.base_link, url)
			# log_utils.log('url = %s' % url)
			result = scraper.get(url, timeout=7).text
			if not result: return sources
			rows = client.parseDOM(result, 'div', attrs={'class': 'tgxtablerow txlight'})
			if not rows: return sources
		except:
			source_utils.scraper_error('TORRENTGALAXY')
			return sources

		undesirables = source_utils.get_undesirables()
		check_foreign_audio = source_utils.check_foreign_audio()
		for row in rows:
			try:
				if 'magnet' not in row: continue
				url = re.search(r'href\s*=\s*["\'](magnet:[^"\']+)["\']', row, re.I).group(1)
				url = unquote_plus(url).split('&tr')[0].replace(' ', '.')
				url = source_utils.strip_non_ascii_and_unprintable(url)
				hash = re.search(r'btih:(.*?)&', url, re.I).group(1)

				name = source_utils.clean_name(url.split('&dn=')[1])
				if not source_utils.check_title(title, aliases, name, hdlr, year): continue
				name_info = source_utils.info_from_name(name, title, year, hdlr, episode_title)
				if source_utils.remove_lang(name_info, check_foreign_audio): continue
				if undesirables and source_utils.remove_undesirables(name_info, undesirables): continue

				if not episode_title: #filter for eps returned in movie query (rare but movie and show exists for Run in 2020)
					ep_strings = [r'[.-]s\d{2}e\d{2}([.-]?)', r'[.-]s\d{2}([.-]?)', r'[.-]season[.-]?\d{1,2}[.-]?']
					if any(re.search(item, name.lower()) for item in ep_strings): continue
				try:
					seeders = int(re.search(r'<span\s*title\s*=\s*["\']Seeders/Leechers["\']>\[<font\s*color\s*=\s*["\']green["\']><b>(.*?)<', row, re.I).group(1))
					if self.min_seeders > seeders: continue
				except: seeders = 0

				quality, info = source_utils.get_release_quality(name_info, url)
				try:
					size = re.search(r'<span\s*class\s*=\s*["\']badge\s*badge-secondary["\']\s*style\s*=\s*["\']border-radius:4px;["\']>(.*?)</span>', row, re.I).group(1)
					dsize, isize = source_utils._size(size)
					info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				append({'provider': 'torrentgalaxy', 'source': 'torrent', 'seeders': seeders, 'hash': hash, 'name': name, 'name_info': name_info, 'quality': quality,
								'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize})
			except:
				source_utils.scraper_error('TORRENTGALAXY')
		return sources

	def sources_packs(self, data, hostDict, search_series=False, total_seasons=None, bypass_filter=False):
		self.sources = []
		if not data: return self.sources
		self.sources_append = self.sources.append
		try:
			self.scraper = cfscrape.create_scraper()
			self.search_series = search_series
			self.total_seasons = total_seasons
			self.bypass_filter = bypass_filter

			self.title = data['tvshowtitle'].replace('&', 'and').replace('Special Victims Unit', 'SVU')
			self.aliases = data['aliases']
			self.imdb = data['imdb']
			self.year = data['year']
			self.season_x = data['season']
			self.season_xx = self.season_x.zfill(2)
			self.undesirables = source_utils.get_undesirables()
			self.check_foreign_audio = source_utils.check_foreign_audio()

			query = re.sub(r'[^A-Za-z0-9\s\.-]+', '', self.title)
			queries = [
						self.search_link % quote_plus(query + ' S%s' % self.season_xx),
						self.search_link % quote_plus(query + ' Season %s' % self.season_x)]
			if search_series:
				queries = [
						self.search_link % quote_plus(query + ' Season'),
						self.search_link % quote_plus(query + ' Complete')]
			threads = []
			append = threads.append
			for url in queries:
				link = '%s%s' % (self.base_link, url)
				append(workers.Thread(self.get_sources_packs, link))
			[i.start() for i in threads]
			[i.join() for i in threads]
			return self.sources
		except:
			source_utils.scraper_error('TORRENTGALAXY')
			return self.sources

	def get_sources_packs(self, link):
		try:
			result = self.scraper.get(link, timeout=7).text
			if not result: return
			rows = client.parseDOM(result, 'div', attrs={'class': 'tgxtablerow txlight'})
			if not rows: return
		except:
			source_utils.scraper_error('TORRENTGALAXY')
			return

		for row in rows:
			try:
				if 'magnet' not in row: continue
				url = re.search(r'href\s*=\s*["\'](magnet:[^"\']+)["\']', row, re.I).group(1)
				url = unquote_plus(url).split('&tr')[0].replace(' ', '.')
				url = source_utils.strip_non_ascii_and_unprintable(url)
				hash = re.search(r'btih:(.*?)&', url, re.I).group(1)

				name = source_utils.clean_name(url.split('&dn=')[1])
				if not self.search_series:
					if not self.bypass_filter:
						if not source_utils.filter_season_pack(self.title, self.aliases, self.year, self.season_x, name): continue
					package = 'season'

				elif self.search_series:
					if not self.bypass_filter:
						valid, last_season = source_utils.filter_show_pack(self.title, self.aliases, self.imdb, self.year, self.season_x, name, self.total_seasons)
						if not valid: continue
					else: last_season = self.total_seasons
					package = 'show'

				name_info = source_utils.info_from_name(name, self.title, self.year, season=self.season_x, pack=package)
				if source_utils.remove_lang(name_info, self.check_foreign_audio): continue
				if self.undesirables and source_utils.remove_undesirables(name_info, self.undesirables): continue
				try:
					seeders = int(re.search(r'<span\s*title\s*=\s*["\']Seeders/Leechers["\']>\[<font\s*color\s*=\s*["\']green["\']><b>(.*?)<', row, re.I).group(1))
					if self.min_seeders > seeders: continue
				except: seeders = 0

				quality, info = source_utils.get_release_quality(name_info, url)
				try:
					size = re.search(r'<span\s*class\s*=\s*["\']badge\s*badge-secondary["\']\s*style\s*=\s*["\']border-radius:4px;["\']>(.*?)</span>', row, re.I).group(1)
					dsize, isize = source_utils._size(size)
					info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				item = {'provider': 'torrentgalaxy', 'source': 'torrent', 'seeders': seeders, 'hash': hash, 'name': name, 'name_info': name_info, 'quality': quality,
							'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize, 'package': package}
				if self.search_series: item.update({'last_season': last_season})
				self.sources_append(item)
			except:
				source_utils.scraper_error('TORRENTGALAXY')