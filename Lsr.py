# Next to do: brainstorm and implement a more efficient flooding mechanism
# then everything should work! thus, implement djikstra's algorithm
import fcntl, os
import errno
import sys
total = len(sys.argv)
cmdargs = str(sys.argv)

import time
from timeit import default_timer as timer

from socket import *

# Parse command line arguments
try:
	myname = sys.argv[1]
	myport = int(sys.argv[2])
	filename = sys.argv[3];
	print "myname = ", myname
	print "myport = ", myport
	print "filename = ", filename
except ValueError:
	print "Error parsing cmd line args"
	sys.exit(1)
	
	
# Read config file
content = [line.split() for line in open(filename)]
	
num_neighbours = int(content[0][0])
del content[0]

#for line in content:
#	for word in line:
#		print word

#                   EXTRACT LINKSTATE
ports = [] # Contains port nums of adjacent nodes
edges = [] # Eventually contains full topology of network
linkstate = '' # String sent to adjacent nodes

for line in content:
#	line = 	['A'] + line
	ports.append(int(line[2]))
	linkstate = linkstate + myname + ' ' + line[0] + ' ' + line[1] + '\n'
	edges.append([myname, line[0], int(line[1])])
	edges.append([line[0], myname, int(line[1])]) #maybe necessary, depends on djistra impl.
	
#print ports
#print edges
#print linkstate

# Create socket
sock =  socket(AF_INET, SOCK_DGRAM)
sock.bind(('127.0.0.1', myport))
fcntl.fcntl(sock, fcntl.F_SETFL, os.O_NONBLOCK)


#-------      FLOODING FUNCTION DEFINITIONS    -------------
# Define function to send data to adjacent nodes
def transmit(sock, ports, data):
	for p in ports:
		sock.sendto(data, ('127.0.0.1', p))
		print 'Sending data to port ', p
	return;
# Define function to send data to adjacent nodes except received node
def retransmit(sock, ports, data, addr):
	for p in ports:
		if addr[1] != p:
			sock.sendto(data, ('127.0.0.1', p))
			print 'Passing on data to port ', p
	return;

def timeout():
	#resend link state data
	transmit(sock, ports, linkstate)
	return;
	
#-------      DIJKSTRA FUNCTION DEFINITIONS    -------------	
def global_dijkstra(edges, myname):
	#print 'Edges: ',edges
	unvisited = [ ] # Simple list of nodes
	node_costs = [ ] # [[node, cost, previous node],[etc... 
	
	# Create list of unvisited nodes
	for edge in edges:
		if edge[0] not in unvisited:
			unvisited.append(edge[0])
			node_costs.append([edge[0], -1, 'Isolated'])
	node_names = list(unvisited) # for displaying the paths we remember all node names
								# SHALLOW COPY
	
	current_node = myname
	current_cost = 0
	while unvisited:
		#find neighbours
		neighbours = find_neighbours(current_node, unvisited, edges)
		#print 'Unvisited: ', unvisited
		#print 'Neighbours of ', current_node, ': ', neighbours
		for neighbour in neighbours:
			#search for edge element with current_node, neighbour
			# (should be only one, so we break afterward)
			for edge in edges:
				if edge[0]==current_node and edge[1] == neighbour:
					neighbour_cost = edge[2] + current_cost
					break
			#Now we have the neighbour cost from current_node
			#If it's smaller, then we update the node_costs
			#First, find the node_costs entry corresponding to this neighbour
			for n in node_costs:
				if n[0] == neighbour:
					if (neighbour_cost < n[1]) or (n[1] == -1):
						#We've found a better cost, update it
						n[1] = neighbour_cost
						n[2] = current_node
						#print 'Updated ', n[0], ' with cost ', n[1], ' predecessor ', n[2]
						break
			#this is done for every neighbour: updating the costs and stuff
		
		#now we're done for looping through the neighbours
		#remove current_node from unvisited (didn't take a for loop!)
		unvisited.remove(current_node)
		
		#new current node will be lowest cost unvisited node (not -1)
		cheapest = -1
		new_node = current_node
		for node_cost in node_costs:
			if ((node_cost[1] < cheapest or cheapest < 0) and node_cost[1] > 0) and (node_cost[0] in unvisited):
				new_node = node_cost[0]
				cheapest = node_cost[1]
		#also update current cost
		current_cost = cheapest
		if new_node == current_node:
			break
		else:
			current_node = new_node
	
	#now we've completed a global search (hooray)
	display_least_cost_paths(node_costs, node_names, myname)
				
	return;

#returns unvisited neighbours of current_node
def find_neighbours(current_node, unvisited, edges):
	neighbours = [ ]
	for edge in edges:
		if edge[0]==current_node and (edge[1] in unvisited) and (edge[1] not in neighbours):
			neighbours.append(edge[1])
		elif (edge[0] in unvisited) and edge[1]==current_node and (edge[0] not in neighbours):
			neighbours.append(edge[0])
	return neighbours;
	
def display_least_cost_paths(node_costs, node_names, myname):
	node_names.sort()
	node_names.remove(myname)
	
	for n in node_names:
		# Find the cost to reach this node from myname
		cost = -1
		for nc in node_costs:
			if nc[0]==n:
				cost = nc[1]
				break
		# Now recursively backtrace the least cost PATH	
		prev = n
		prev_nodes = [n]
		while prev != myname:
			prev = find_predecessor(prev, node_costs)
			prev_nodes.insert(0,prev)
			if prev == 'Error m8':
				break
		
		# Finally print what we want to see
		print 'Least cost path to node ', n, ' : ', prev_nodes, ' with cost: ', cost
	return;
	
def find_predecessor(node, node_costs):
	for nc in node_costs:
		if nc[0] == node:
			return nc[2]
	return 'Error m8'

	
# Transmit linkstate packet, start timer
tic = timer()
dijkstra_tic = timer()
transmit(sock, ports, linkstate)

# List to contain past transmissions (for efficient flooding)
past_transmits = [linkstate]
full_past_transmits = [linkstate] # not reset every transmit_time, for adding new edges

while 1:
	
	toc = timer()
	if toc - tic >= 1:
		transmit(sock, ports, linkstate)
		past_transmits = [linkstate] # reset memory of duplicate transmissions
		tic = timer()
		
	dijkstra_toc = timer()
	if dijkstra_toc - dijkstra_tic > 5:
		global_dijkstra(edges, myname)
		dijkstra_tic = timer()
	
	# Listen for anything from SOCK
	try:
		msg, addr = sock.recvfrom(1024)
	except error, e:
		err = e.args[0]
		if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
            #sleep(1)
			#print 'No data available'
			pass
		else:
            # a "real" error occurred
			print e
			sys.exit(1)
	else:
        # got a message, do something :)
		#print 'Received a message: ', msg, 'from port ', addr[1]
		new_message = 1
		for past_message in past_transmits:
			if past_message == msg:
				new_message = 0
		if new_message == 1:
		# Retransmit message to other adjacent nodes
			retransmit(sock, ports, msg, addr)
			past_transmits.append(msg)
			
			
			# Check if new data for adding to topology knowledge
			new_message = 1
			for past_message in full_past_transmits:
				if past_message == msg:
					new_message = 0
			if new_message == 1:
				print 'unseen message'
				print edges
				full_past_transmits.append(msg)
				# Append into edges list
				line = msg.split()
				#print line
				for i in xrange(0, len(line), 3):
					edges.append([line[i], line[i+1], int(line[i+2])]) #reverse will also naturally come in (i+1, i)
					
		
        
	   
    
        

	

