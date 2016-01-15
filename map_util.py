import pickle
import os
import sys

TEXT_RENDER_WIDTH = 60

ASPECT_RATIO = 16.0/9.0
DEFAULT_ZOOM = 10.0

class MapfileError(Exception):
	def __init__(self, mapfile=None):
		if mapfile:
			msg = "MapfileError: Problem with map-file: \"%s\", does not seem to be of the required format.\n" % os.path.basename(mapfile)
			print(msg, file=sys.stderr)

class MapBuilder:
	"""
	@brief      This is used for testing and debugging. Used only map generation. Once genersted, use Map to read.
	"""
	def __init__(self, mf=None, zoom=DEFAULT_ZOOM, aspect=ASPECT_RATIO, retrieve=False):
		self.mfile = mf
		self.servers = {}
		self.zoom = zoom
		self.aspect = aspect
		self.labeled = False

		if retrieve:
			self.retrieve()
		
	def get_servers(self):
		print("Server details now! 'q' to exit")
		print("<X ratio> <Y ratio> <initial power>")
		while True:
			user_input = input("> ")
			if user_input == 'q':
				break
			else:
				details = user_input.split()
				if len(details) != 3:
					print("Invalid Response!\n")
					continue
				else:
					try:
						x = float(details[0])
						y = float(details[1])
						p = int(details[2])
						if x < 0.0 or x > 1.0 or y < 0.0 or y > 1.0:
							raise
						else:
							self.servers[(x, y)] = p
					except Exception as e:
						print(e)
						print("Invalid Row and/or Col and/or Power! (%f, %f)\n" % (x, y))
						continue
					print(self.pretty()+'\n')
		# add only those servers which have non-zero initial power
		self.validate()
		# label all the servers.
		self.label_servers()		

	def validate(self):
		# rebuild the server dict, only those which have non-zero power
		actual = {}
		for loc in self.servers.keys():
			if self.servers[loc] > 0:
				transformed = ( loc[0]*self.zoom, loc[1]*self.zoom)
				actual[loc] = self.servers[loc]
		self.servers = actual
		self.server_count = len(actual)

	def pretty(self):
		def transform(virtual_coord):
			xmod, ymod = virtual_coord
			return int(ymod * TEXT_RENDER_WIDTH / ASPECT_RATIO), int(xmod*TEXT_RENDER_WIDTH)
		
		ROWS = int(TEXT_RENDER_WIDTH / ASPECT_RATIO)
		COLS = TEXT_RENDER_WIDTH
		
		tr_servers = {}
		for loc in self.servers.keys():
			print("Rendered", loc, "@", transform(loc))
			tr_servers[transform(loc)] = self.servers[loc]
		
		mapstr = ""
		for r in range(ROWS):
			row = ""
			for c in range(COLS):
				if (r, c) in tr_servers.keys():
					if self.labeled:
						row += ("%d" % tr_servers[(r, c)]["power"])
					else:
						row += ("%d" % tr_servers[(r, c)])
				else:
					row += (".")
			mapstr += row+'\n'
		return mapstr

	
	def label_servers(self):
		print("You will now be asked to label the servers into clusters one by one.\nUse integers from 0 onwards.\n-1 denotes neutral servers.\n")
		labeled = [False for _ in self.servers.keys()]
		clusters = {}
		actual_servers = {}
		locations = [l for l in self.servers.keys()]
		index = 0
		while index < len(locations):
			loc = locations[index]
			while True:
				try:
					user_input = int(input("(%f, %f) is " % (loc[0], loc[1])))
					if user_input < -1:
						print("Invalid Response!")
					else:
						server = {	"owner" : user_input,
									"coord" : loc,
									"power" : self.servers[loc]}
						if user_input in clusters.keys():
							clusters[user_input].append(server)
						else:
							clusters[user_input] = [server]
						index += 1
						break
				except Exception as e:
					print(e+'\n')				
			actual_servers[loc] = server
		
		# find bot count, remove neutrals with group_id == -1
		groups = [g for g in clusters.keys()]
		self.bot_count = 0
		for g in groups:
			if g > -1:
				self.bot_count += 1

		self.clusters = clusters
		self.servers = actual_servers
		self.labeled = True

	def save(self):
		# save all data
		map_data = {"aspect"       : self.aspect,
					"server_count" : self.server_count,
					"servers"      : self.servers,
					"clusters"     : self.clusters,
					"zoom"         : self.zoom,
					"bot_count"    : self.bot_count}

		pickle.dump(map_data, open(os.path.join("maps", self.mfile), 'wb'))

	def retrieve(self):
		# returns map_data dictionary that was read from the file!
		map_data = pickle.load(open(os.path.join("maps", self.mfile), 'rb'))
		self.server_count = map_data["server_count"]
		self.servers      = map_data["servers"]
		self.clusters     = map_data["clusters"]
		self.zoom         = map_data["zoom"]
		self.aspect       = map_data["aspect"]
		self.bot_count    = map_data["bot_count"]
		self.labeled = True
		print(self.clusters)
		return map_data

class Map:
	"""
	@brief      This class only reads the pickled map, hopefully it's correctly formatted.
	"""
	def __init__(self, mapfile):
		try:
			options = pickle.load(open(os.path.join("maps", mapfile), 'rb'))
			self.zoom         = options["zoom"]
			self.aspect       = options["aspect"]
			self.server_count = options["server_count"]
			self.clusters     = options["clusters"]
			self.bot_count    = options["bot_count"]
		except Exception as e:
			print(e, file=sys.stderr)
			raise MapfileError(mapfile)

	def show(self, width=TEXT_RENDER_WIDTH, aspect=None):
		if not aspect:
			aspect = self.aspect
		def transform(virtual_coord):
			xmod, ymod = virtual_coord
			return int(ymod * width / aspect), int(xmod*width)
	
		ROWS = int(width / aspect)
		COLS = width
		
		tr_servers = {}
		for group in self.clusters.keys():
			for server in self.clusters[group]:
				loc = server["coord"]
				print("Rendered", loc, "@", transform(loc))
				tr_servers[transform(loc)] = server["power"]
		
		mapstr = ""
		for r in range(ROWS):
			row = ""
			for c in range(COLS):
				if (r, c) in tr_servers.keys():
					row += ("%d" % tr_servers[(r, c)])
				else:
					row += (".")
			mapstr += row+'\n'
		return mapstr

if __name__ == "__main__":
	ch = input("Build a new map? ")
	if len(ch) > 0 and ch in "yY":
		fname = input("New map-file name? [.map] will be added automatically.\n> ")
		m = MapBuilder(fname+".map", retrieve=False)
		m.get_servers()
		m.save()
	else:
		print("Not making new map.")
		fname = input("Read which map-file? [.map] will be added automatically.\n> ")
		m = MapBuilder(fname+".map", retrieve=True)
		print(m.pretty())
		print("botCount =",m.bot_count)