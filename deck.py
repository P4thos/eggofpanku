# Egg of P'an Ku -- an unofficial client for Legend of the Five Rings
# Copyright (C) 2008  Peter C O Johansson
# 
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
"""Deck module for Egg of P'an Ku."""
import database
from enums import Enumeration

OUTPUT_TYPES = Enumeration("OUTPUT_TYPES",['Text','HTML','BBCode'])

class DeckException(Exception):
	pass

class ImportCardsNotFoundError(DeckException):
	def __init__(self, cardErrors, deck):
		self.problemCards = cardErrors
		self.importedDeck = deck
	def __str__(self):
		errorStr = (''.join(['%s\r\n' % line for line in self.problemCards]))
		return "These cards were unable to be imported:\r\n%s" % errorStr
			
	
class InvalidCardError(DeckException):
	def __init__(self, card):
		self.card = card
	def __str__(self):
		return "Card '%s' not found in database." % self.card


class Deck:
	
	
	def __init__(self):
		self.cards = []
		self.modified = False
	
	def __iter__(self):
		return self.cards.__iter__()
	
	def __len__(self):
		return len(self.cards)
	
	def NumDynasty(self):
		"""Return the number of dynasty cards in the deck."""
		db = database.get()
		return sum([count for count, id in self.cards if db[id].isDynasty()])
	
	def NumFate(self):
		"""Return the number of fate cards in the deck."""
		db = database.get()
		return sum([count for count, id in self.cards if db[id].isFate()])
	
	@classmethod
	def load(cls, fp):
		"""Read a deck from a list of strings (or a file-like object) and parse it.
		
		Returns a deck object.
		
		"""
		db = database.get()
		deck = Deck()
		for c in fp:
			if not c.startswith('#') and c.strip() != '':
				(count, cardname) = c.strip().split(' ', 1)
				cardname = cardname.strip()
				try:
					deck.cards.append((int(count), db.FindCardByName(cardname).id))
				except KeyError:
					raise InvalidCardError(cardname)
		return deck

	@classmethod
	def loadFromClipboard(cls, data):
		#set up a holder for unknown cards
		cardErrors= []
		importLineHeaders = ['stronghold','dynasty','holdings','regions','personalities','events','fate','actions','spells','items','followers','rings']
		
		db = database.get()
		deck = Deck()

		#Look for a card line, not a header, not a space, and not the EOF (\x00) line.
		for line in data.splitlines():
			if not line.startswith('#') \
			and line.find('\x00') == -1 \
			and line.find(':') == -1 \
			and line.strip() != '' \
			and not line.isspace():
				try:
					#check that the first item is an integer
					cardStr = line.strip().split(' ', 1)
					cardLower = cardStr[0].lower()
					if  cardLower in importLineHeaders:
						continue
					
					count = cardStr[0].strip('x')
					if count.isdigit():				
						cardname =  cardStr[1].strip()
					else:
						count = 1
						cardname = line.strip()
				except (ValueError, IndexError):
						count = 1
						cardname = line.strip()
				try:
					deck.cards.append((int(count), db.FindCardByName(cardname).id))
				except (ValueError,KeyError):
					cardErrors.append(cardname)

		#If there are errors throw an import error.
		if len(cardErrors) > 0:
			raise ImportCardsNotFoundError(cardErrors, deck)
		
		return deck

	def Save(self, fp, savetype):
		db = database.get()

		headerString = ''
		headerString = {OUTPUT_TYPES.Text:'\n# %s (%d)\n',
						OUTPUT_TYPES.HTML:'\n<h3><u>%s (%d)</u></h3>\n',
						OUTPUT_TYPES.BBCode:'\n[size=150]%s (%d)[/size]\n'}[savetype]
		
		for count, cdid in self:
			card = db[cdid]
			if card.type == 'strongholds':
				shString = {OUTPUT_TYPES.Text:'\n1 %s\n',
							OUTPUT_TYPES.HTML:'\n<h3><u>%s</u></h3>\n',
							OUTPUT_TYPES.BBCode:'\n[size=150]%s[/size]\n'}[savetype]
				fp.write(shString % (card.name))
		#Dynasty Deck
		dyncards = [(count, db[cdid]) for count, cdid in self if db[cdid].isDynasty()]
		dynCount = 0
		for item in dyncards:
			dynCount += int(item[0])

		fp.write(headerString % ('Dynasty',dynCount))

		eventcards = [(count, db[cdid]) for count, cdid in self if db[cdid].isEvent()]
		self.WriteCardsToTypeList(fp,eventcards,'Events', savetype)

		regioncards = [(count, db[cdid]) for count, cdid in self if db[cdid].isRegion()]
		self.WriteCardsToTypeList(fp,regioncards,'Regions', savetype)

		holdingcards = [(count, db[cdid]) for count, cdid in self if db[cdid].isHolding()]
		self.WriteCardsToTypeList(fp,holdingcards,'Holdings', savetype)

		windcards = [(count, db[cdid]) for count, cdid in self if db[cdid].isWind()]
		self.WriteCardsToTypeList(fp,windcards,'Winds', savetype)

		personalitycards = [(count, db[cdid]) for count, cdid in self if db[cdid].isPersonality()]
		self.WriteCardsToTypeList(fp,personalitycards,'Personalities', savetype)


		#Fate Deck
		fatecards = [(count, db[cdid]) for count, cdid in self if db[cdid].isFate()]
		fateCount = 0
		for item in fatecards:
			fateCount += int(item[0])

		#fatecards.sort(lambda a, b: cmp(a[1].type, b[1].type))
		fp.write(headerString % ('Fate',dynCount))

		ancestorcards = [(count, db[cdid]) for count, cdid in self if db[cdid].isAncestor()]
		self.WriteCardsToTypeList(fp,ancestorcards,'Ancestors', savetype)

		actioncards = [(count, db[cdid]) for count, cdid in self if db[cdid].isAction()]
		self.WriteCardsToTypeList(fp,actioncards,'Actions', savetype)

		followercards = [(count, db[cdid]) for count, cdid in self if db[cdid].isFollower()]
		self.WriteCardsToTypeList(fp,followercards,'Followers', savetype)


		itemcards = [(count, db[cdid]) for count, cdid in self if db[cdid].isItem()]
		self.WriteCardsToTypeList(fp,itemcards,'Items', savetype)

		spellcards = [(count, db[cdid]) for count, cdid in self if db[cdid].isSpell()]
		self.WriteCardsToTypeList(fp,spellcards,'Spells', savetype)

		ringcards = [(count, db[cdid]) for count, cdid in self if db[cdid].isRing()]
		self.WriteCardsToTypeList(fp,ringcards,'Rings', savetype)

		senseicards = [(count, db[cdid]) for count, cdid in self if db[cdid].isSensei()]
		self.WriteCardsToTypeList(fp,senseicards,'Senseis', savetype)



	def WriteCardsToTypeList(self, fp, cardlist, title, saveType):
		"""Writes all the cards to a typed list, for display and saving"""
		#Added 11/24/08 PCW
		headerString = ''
		cardString = ''
			
		if len(cardlist) > 0:
			cardCount = 0
			for item in cardlist:
				cardCount += int(item[0])

			headerString = {OUTPUT_TYPES.Text:'\n# %s (%d)\n',
							OUTPUT_TYPES.HTML:'\n<b><u>%s (%d)</u></b>\n',
							OUTPUT_TYPES.BBCode:'\n[b][u]%s (%d)[/u][/b]\n'}[saveType]
				
			cardlist.sort(lambda a, b: cmp(a[1].type, b[1].type))
			cardString = {OUTPUT_TYPES.Text:'%d %s\n',
						  OUTPUT_TYPES.HTML:'%d %s<br/>\n',
						  OUTPUT_TYPES.BBCode:'%d %s\n'}[saveType]
			
			fp.write(headerString % (title,cardCount))
			for count, card in cardlist:
				fp.write(cardString % (count, card.name))

	def Add(self, cdid, num = 1):
		"""Add a number of a particular card to the deck.
		
		Returns the number of that card now in the deck.
		
		"""
		for idx, val in enumerate(self.cards):
			if val[1] == cdid:
				self.cards[idx] = (val[0] + num, cdid)
				return val[0] + num
		self.cards.append((num, cdid))
		return num

	def Remove(self, cdid, num = 1):
		"""Remove a number of a particular card from the deck.
		
		Returns the number of that card now in the deck.
		
		"""
		for idx, val in enumerate(self.cards):
			if val[1] == cdid:
				if val[0] > num:
					self.cards[idx] = (val[0] - num, cdid)
					return val[0] - num
				else:
					del self.cards[idx]
					return 0
		return 0
