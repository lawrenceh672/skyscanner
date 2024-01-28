# -*- coding: utf-8 -*-
"""
Created on Fri Nov 15 13:46:06 2019

@author: Larry
"""
import datetime
import cv2
import numpy as np
import pandas as pd

class Tracked:
	ID=0
		
	def __init__(self, frame_start):
		"""self.x = int(rect[0])
		self.y = int(rect[1])
		self.w = int(rect[2])
		self.h = int(rect[3])"""

		self.frame_start=int(frame_start)
		self.frame_end=int(frame_start) #Its got at least one active frame, its creation
		self.active=True #is it still being tracked?
		self.classification = None
		self.ID = Tracked.ID
		Tracked.ID += 1
		self.xywh_track = []
	
	def addTrackingSquare(self, rect):
		self.xywh_track.append(rect)
		self.frame_end += 1 #One more frame in the TO
		return True

	def __str__(self):
		ret = "ID: {} [{}-{}]".format(self.ID, self.frame_start, self.frame_end)
		return ret

	def RectPointOne(self):
		#Return a tuple (x,y)
		(x,y,w,h) = self.lastSquare()
		return (x, y)

	def RectPointTwo(self):
		#return the tuple of point 2 in the rectangle
		#Return a tuple (x+w,y+h)
		(x,y,w,h) = self.lastSquare()
		return (x + w, y + h)

	def activeAtFrame(self, index):
		if (index >= self.frame_start) and (index < self.frame_end):
			return True
		else:
			return False
		return False
	
	def toPNG(self, filename, frame):
		cv2.imwrite(filename, frame) #for now its just the first frame as the base image
		
	def classify(self, frame, min_confidence):
		print("Classifying: " + str(self))
		return "Default Classifier"

	def xywhAt(self, frame):
		index = frame - self.frame_start
		try:
			ret = self.xywh_track[index]
		except IndexError:
			print("xywh index out of range")
			return None
		return self.xywh_track[index]

	def lastSquare(self):
		x = self.xywh_track[-1][0]
		y = self.xywh_track[-1][1]
		w = self.xywh_track[-1][2]
		h = self.xywh_track[-1][3]
		return (x,y,w,h)

	def lastFrameIndex(self):
		return self.frame_start + len(self.xywh_track)

#####################	END OF CLASS	############################################################################
		
def TrackedSnapShot(frameIndex, history):
	#{(frameIndex):[toid, (x,y,w,h)],...}
	#loop through all objects in history, find the ones where frameIndex is between start and end
	ret = {}

	for to in history:
		if to.activeAtFrame(frameIndex) == True: #If the object identifies as being in range
			#Calculate how many frames in frameIndex is into this objects lifespan
			indent = frameIndex - to.frame_start
			#Load the tuple from it tracked list and append it to the list of active tracked objects at this frame
			try:
				ret[frameIndex] = [to.ID, to.xywh_track[indent]]
			except IndexError:
				print("Exception in TrackedSnapShot")
	return ret

def TrackedActiveFrameList(history):  #return of list of every frame that had any activity
	#{frameindex1:{tracking object ID: square}}
	ret = {}
	#Possibly change to dictionary and attach a value of a list of tracking squares to each frame
	for to in history:
		start = to.frame_start
		end = to.frame_end
		for i in range(start, end):
			xywh = to.xywhAt(i) #Get the tracking square at this frame index i
			if i not in ret: #This frame isnt in the index
				inner = {}
				inner.update({to.ID: xywh})
				ret.update({i: inner})
			else: #The frame has been recorded with activity, update the frameindex to show the new tracking square active on it
				inner = ret[i] #get the existing dict of tracking squares in this frame
				inner.update({to.ID: xywh})
				ret.update({i : inner})
	return ret
