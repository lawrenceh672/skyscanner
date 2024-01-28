import datetime
from SkyScanner_DB import bbdb
import cv2
from pynput.keyboard import Key
from Globals import Globals
import numpy as np

class Classifier(object):
	def __init__(self, *args):
		#Get all the classification names
		self.load(args[0]) #Load the incoming name which should be the first argument

	def load(self, name):
		self.name = name
		db = bbdb(Globals.get("DB"))
		self.samples = db.getClassificationSampleImages(self.name) #A list of the classification sample images selected by the user
		classifierDBRow = db.getClassifier(self.name) #Get the image classifier from the database, as pandas dataframe
		#Now move the elements from the data frame into the python object
		self.classifier = classifierDBRow['CLASSIFIER'] #The binary object that holds the classification object
		self.last_run = int(classifierDBRow['LAST_RUN'])
		self.sample_depth = classifierDBRow['SAMPLE_DEPTH']
		self.numberSamples = len(self.samples)
		self.frameIndex = 0
		self.classifierList = db.getAllClassificationNames() #A list of all the classifiers currently added

	def __str__(self):
		ret = "Classifier {}\n".format(self.name)
		ret += "{} Samples.  Sample depth {}\n".format(self.numberSamples, self.sample_depth)
		if self.last_run == 0:
			comp = False
		else:
			comp = True
		ret += "Classifier compiled: {}".format(comp)
		return ret

#Might be useful for drawing frames with tracking boxes on it
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
			cv2.putText(frame,str(TrackingObjectID),(int(x+w/2), int(y+h/2)),cv2.FONT_HERSHEY_SIMglobalsLEX,0.5,(255, 255, 255),2)

		#Draw the user selection
		for (coords, description) in self.classifications.items():
			start = coords[0] #Get the user classification
			end = coords[1]
			cv2.rectangle(frame, start, end, (255, 255, 255), 2)
			cv2.putText(frame,description,start,cv2.FONT_HERSHEY_SIMPLEX,0.5,(255, 255, 255),2)	
		#cv2.imshow("Classifier sample selector", frame)
		return frame
	def setFrame(self, frameindex):
		#Change the frame being displayed and worked on
		#get movement tracking boxes
		bbv = Globals.get("BB Video Results")
		db = bbdb(Globals.get("DB"))

		self.frameIndex = frameindex
		try:
			self.trackingBoxes =  bbv.TrackingBoxes[frameindex] #rectangles showing observed movement by the BB algorithm
		except Exception as E:
			self.trackingBoxes = {}
		#get classification samples as set by the user
		try:
			self.classifications = bbv.ClassifierSamples[frameindex]
		except Exception as E:
			self.classifications = {} #Nothing on this frame

		(path, self.frame) = bbv.getHRImagePath(db, self.frameIndex)
		return self.drawScreen()







