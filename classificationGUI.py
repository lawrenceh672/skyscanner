from DB_utilities import bbdb
import cv2
import threading
from pynput.keyboard import Key, Listener
import numpy as np
import threading

class classificationGUI():
	#A thread class to take in and store a video feed, splitting it up into regular sized file chunks
	#def __init__(self, bbv, frameIndex, dbFileName):
	def __init__(self, *args):
		self.bbv = args[0] #The BBVideo, the dbfilename to open a new db connection and the frameIndex to work on
		self.dbFileName = args[2]
		self.frameIndex = args[1]
		self.inputt = args[3]
		self.db = bbdb(self.dbFileName)
		self.pressed = ""
		# Collect events until released
		self.classifications = {} #the classifications available on this frame {((x1,y1),(x2,y2)): "name"}
		self.returnCount = 0 #How many classifiers are selected
		self.setFrame(self.frameIndex)
		frame = self.drawScreen()
		cv2.setMouseCallback("Classifier sample selector", self.mouse_click)
		self.ROI = False #If the user selects something it'll be(box, image)
		self.running = True
		self.startROI = False #When the user starts the ROI routine turn to true to signal parent thread


	def __str__(self):
		ret = "Classifier window {} in {}".format(self.frameIndex, self.bbv.path)
		return ret

	def drawScreen(self):
		frame = np.copy(self.frame) #Get the original unadultered frame
		#Draw in the tracking boxes
		for (TrackingObjectID, rect) in self.trackingBoxes.items():
			x = int(rect[0])
			y = int(rect[1])
			w = int(rect[2])
			h = int(rect[3])
			start = (x, y) #Take the 4 points x y w h and make it rectangles for openbcv
			end = (x+w,y+h)
			cv2.rectangle(frame, start, end, (255, 255, 255), 2)
			cv2.putText(frame,str(TrackingObjectID),(int(x+w/2), int(y+h/2)),cv2.FONT_HERSHEY_SIMPLEX,0.5,(255, 255, 255),2)

		#Draw the user selection
		for (coords, description) in self.classifications.items():
			start = coords[0] #Get the user classification
			end = coords[1]
			cv2.rectangle(frame, start, end, (255, 255, 255), 2)
			cv2.putText(frame,description,start,cv2.FONT_HERSHEY_SIMPLEX,0.5,(255, 255, 255),2)	
		cv2.imshow("Classifier sample selector", frame)
		cv2.waitKey(1)

	def setFrame(self, frameindex):
		#Change the frame being displayed and worked on
		#get movement tracking boxes
		self.frameIndex = frameindex
		try:
			self.trackingBoxes =  self.bbv.TrackingBoxes[frameindex] #rectangles showing observed movement by the BB algorithm
		except Exception as E:
			self.trackingBoxes = {}
		#get classification samples as set by the user
		try:
			self.classifications = self.bbv.ClassifierSamples[frameindex]
		except Exception as E:
			self.classifications = {} #Nothing on this frame

		(path, self.frame) = self.bbv.getHRImagePath(self.db, self.frameIndex)
		self.drawScreen()


	def mouse_click(self, event, x, y, flags, param):
		#to check if left mouse 
	    # button was clicked
		if event == cv2.EVENT_LBUTTONDOWN:
			self.startROI = True #Signal to the parent thread the user clicked something


	def stop():
		cv2.destroyWindow("Classifier sample selector")

