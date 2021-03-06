from __future__ import print_function
import sys
import traceback
import random
import time
import util

STATE_MAP = util.Connection.STATE_MAP
INV_ST_MAP = util.Connection.INV_ST_MAP

class UnkownGameStateParameter(Exception):
	def __init__(self, line=None, key=None):
		if line and key:
			msg = "Unrecognised format. Found this line, \"%s\"\nkey=\"%s\", is not understood or data format is wrong.\nSomething wrong with saber/quantum.py\n" % (line, key)
			print(msg, file=sys.stderr)
		else:
			print("Unrecognised format.\n", file=sys.stderr)
		raise RuntimeError

class ServerStack():
	"""
	Actual game-state as seen by "this" ServerStack
	"""
	def __init__(self):
		# all state variable, rows, cols, nodes, etc
		self.turntime = 0
		self.loadtime = 0
		self.turn = 0

		self.active = True
		self.Clusters = {}
		self.Servers = []

		self.news_deletions = []
		self.news_additions = []
		self.news_alerts = []
	
	def setup(self, start_data):
		"""
		empty lines and lines without '~' are ignored
		"""
		lines = start_data.split('\n')
		for line in lines:
			try:
				key, data = line.strip().split('~')
			except ValueError:
				# this happens because of the last newline which results in lines.split('\n') to be == [... , '...', '']
				# and the last item cannot be unpacked into (key, data)
				continue
			if key == 'turn':
				self.turn = int(data)
			elif key == 'turntime':
				self.turntime = int(data)
			elif key == 'loadtime':
				self.loadtime = int(data)
			elif key == 'id':
				self.my_id = int(data)
			elif key == 'act_width':
				self._actual_width = float(data)
			elif key == 'aspect':
				self._aspect = float(data)
			elif key in 'ns' and key != 'ns':
				try:
					sid, x, y, reserve, invested, limit, owner = data.split()
					self.Servers.append(util.Server((float(x), float(y)), float(reserve) + float(invested), float(limit), float(owner), int(sid)))
					if int(owner) in self.Clusters.keys():
						self.Clusters[int(owner)].append(int(sid))
					else:
						self.Clusters[int(owner)] = [int(sid)]
				except:
					raise UnkownGameStateParameter(line, key)
			elif key == 'bot_count':
				self.bot_count = int(data) # number of other bots
			elif key == 'server_count':
				self.server_count = int(data) # number of other bots
			else:
				raise UnkownGameStateParameter(line, key)
		if self.active == True:
			self.my_nodes    = self.Clusters[self.my_id]
			self.enemy_nodes = [server.index for server in self.Servers if server.owner != self.my_id and server.owner != -1]
			self.neutrals    = [server.index for server in self.Servers if server.owner == -1]

	def update_state(self, up_data):
		"""
		empty lines and lines without '~' are ignored
		"""
		self.news_deletions = []
		self.news_additions = []
		self.news_alerts = []
		lines = up_data.split('\n')
		_clusters = {}
		for line in lines:
			try:
				key, data = line.strip().split('~')
			except ValueError:
				# this happens because of the last newline which results in lines.split('\n') to be == [... , '...', '']
				# and the last item cannot be unpacked into (key, data)
				continue
			if key == 'turn':
				self.turn = int(data)
			elif key == 'score':
				self.score = float(data)
			elif key == 's':
				try:
					sid, reserve, invested, owner = data.split()
					self.Servers[int(sid)].sync(float(reserve), float(invested), int(owner))
					if int(owner) in _clusters.keys():
						_clusters[int(owner)].append(int(sid))
					else:
						_clusters[int(owner)] = [int(sid)]
				except:
					raise UnkownGameStateParameter(line, key)
			elif key == 'cd':
				try:
					epoch_pct, a_sid, v_sid, _state = data.split()
					if v_sid in self.Servers[int(a_sid)].connections.keys():
						# a 'whostile' is deleted
						del self.Servers[int(a_sid)].connections[v_sid]
						self.news_deletions.append((float(epoch_pct), int(a_sid), v_sid, int(_state)))
					else:
						# a 'withdrawing' is deleted
						del self.Servers[int(a_sid)].connections[int(v_sid)]
						self.news_deletions.append((float(epoch_pct), int(a_sid), int(v_sid), int(_state)))
				except:
					raise UnkownGameStateParameter(line, key)
			elif key == 'cn':
				try:
					a_sid, v_sid, arate, fdist, _state = data.split()
					try:
						a_sid, v_sid, arate, fdist, _state = int(a_sid), int(v_sid), float(arate), float(fdist), int(_state)
						self.Servers[a_sid].new_connection(v_sid, arate, fdist, _state)
						self.news_additions.append((int(a_sid), int(v_sid), float(arate), float(fdist), int(_state)))
					except (KeyError, ValueError):
						a_sid, v_sid, arate, fdist, _state = int(a_sid), v_sid, float(arate), float(fdist), int(_state)
						self.Servers[a_sid].new_connection(v_sid, arate, fdist, _state)
						self.news_additions.append((int(a_sid), v_sid, float(arate), float(fdist), int(_state)))
				except:
					raise UnkownGameStateParameter(line, key)
			elif key == 'c':
				try:
					a_sid, v_sid, arate, state, length = data.split()
					try:
						a_sid, v_sid, arate, state, length = int(a_sid), int(v_sid), float(arate), int(state), float(length)
						self.Servers[a_sid].connections[v_sid].sync(arate, state, length)
					except (KeyError, ValueError):
						a_sid, v_sid, arate, state, length = int(a_sid), v_sid, float(arate), int(state), float(length)
						self.Servers[a_sid].connections[v_sid].sync(arate, state, length)
				except:
					raise UnkownGameStateParameter(line, key)
			elif key == 'A':
				try:
					_mode, turn_no, epoch_pct, info1, info2, info3 = data.split()
					turn_no, epoch_pct = int(turn_no), float(epoch_pct)
					if _mode in 'wp':
						info1, info2, info3 =  int(info1), int(info2), int(info3)
					elif _mode == 'i':
						info1, info2, info3 =  int(info1), int(info2), float(info3)
					self.news_alerts.append((turn_no, epoch_pct, _mode, info1, info2, info3))
				except:
					raise UnkownGameStateParameter(line, key)
		self.Clusters = _clusters
		if self.active == True:
			self.my_nodes    = self.Clusters[self.my_id]
			self.enemy_nodes = [server.index for server in self.Servers if server.owner != self.my_id and server.owner != -1]
			self.neutrals    = [server.index for server in self.Servers if server.owner == -1]

	def dist_between(self, id1, id2):
		"""
		@brief      Computes (obviously, the shortest) distance between 2 servers(nodes)
		
		@param      self  game-state object
		@param      id1   id of server1
		@param      id2   id of server2
		
		@return     # of routers on the shortest path between the 2 given servers.
		"""
		p1 = self.Servers[id1].pos
		p2 = self.Servers[id2].pos
		return ( ((p1[0]-p2[0])*self._actual_width)**2 + ((p1[1]-p2[1])*self._actual_width/self._aspect)**2 )**0.5

	def attack(self, sid, tid, arate):
		sys.stdout.write( "a %d %d %f\n" % (sid, tid, arate) )
		sys.stdout.flush()

	def update_link(self, sid, tid, arate):
		sys.stdout.write( "u %d %d %f\n" % (sid, tid, arate) )
		sys.stdout.flush()

	def withdraw(self, sid, tid, split):
		sys.stdout.write( "w %d %d %f\n" % (sid, tid, split) )
		sys.stdout.flush()

	# helper functions
	def error_dump(self, whatever):
		sys.stderr.write(str(whatever)+"\n")
		sys.stderr.flush()

	def pretty_dump_alerts(self):
		if self.news_alerts:
			for notice in self.news_alerts:
				turn_no, epoch_pct, _mode, info1, info2, info3 = notice
				if _mode == 'p':
					message = "%d's %d pawned your server %d! @ turn(%d)+%2.4f" % (info1, info2, info3, turn_no, epoch_pct)
				elif _mode == 'w':
					message = "Server %d is \"in-danger\". Game 'auto-withdrew' connection to %d (state:'%s') @ turn(%d)+%2.4f" % (info1, info2, INV_ST_MAP[info3], turn_no, epoch_pct) 
				elif _mode == 'i':
					message = "Turn %4d: Can't attack %d from %d due to insufficient resource. Need %f" % (turn_no, info1, info2, info3)
				self.error_dump(message)

	def pretty_dump_additions(self):
		if self.news_additions:
			for asid, vsid, arate, fdist, state in self.news_additions:
				try:
					message = "A new Connection from %d to %d (arate=%f; distance=%f) was made of type:%s @ t%d" % (asid, vsid, arate, fdist, INV_ST_MAP[state], self.turn)
				except:
					message = "A new Connection from %d to %s* (arate=%f; distance=%f) was made of type:%s @ t%d" % (asid, vsid, arate, fdist, INV_ST_MAP[state], self.turn)
				self.error_dump(message)

	def pretty_dump_deletions(self):
		if self.news_additions:
			for notice in self.news_deletions:
				epct, asid, vsid, state = notice
				try:
					message = "Connection from %d to %d of type:%s was deleted @ t%d+%f!" % (asid, vsid, INV_ST_MAP[state], self.turn, epct)
				except:
					message = "Connection from %d to %s* of type:%s was deleted @ t%d+%f!" % (asid, vsid, INV_ST_MAP[state], self.turn, epct)
				self.error_dump(message)

	@staticmethod
	def launch(bot=None):
		game_state = ServerStack()
		map_data = ''
		while game_state.active:
			try:
				cline = sys.stdin.readline().rstrip('\n\r')
				if cline == "":
					continue
				elif cline == 'ready':
					game_state.setup(map_data)
					if bot:
						bot.do_setup(game_state)
					sys.stdout.write("go\n")
					sys.stdout.flush()
					map_data = ''
				elif cline == "go":
					game_state.update_state(map_data)
					if bot and game_state.active:
						bot.do_turn(game_state)
					sys.stdout.write("go\n")
					sys.stdout.flush()
					map_data = ''
				else:
					map_data += cline + '\n'
			except EOFError:
				break
			except KeyboardInterrupt:
				raise
			except:
				traceback.print_exc(file=sys.stderr)
				sys.stderr.flush()

if __name__ == '__main__':
	ss = ServerStack()
	ss.launch(None)