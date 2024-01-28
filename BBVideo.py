from Tracked import TrackedSnapShot, TrackedActiveFrameList
import pandas as pd
import cv2
#from PIL import Image
import base64
from io import BytesIO
from imutils.video import FileVideoStream
import matplotlib.pyplot as plt
from Globals import Globals
from SkyScanner_DB import bbdb

class VideoFileMetaInformation():
	#A class to store meta information about a file in the file system
	def __init__(self, path):
		#Load the file from the video system
		self.vs = cv2.VideoCapture(path)
		self.frame_count = int(self.vs.get(cv2.CAP_PROP_FRAME_COUNT)) #The total number of frames in the video
		self.width = self.vs.get(3)
		self.height = self.vs.get(4)
class BBVideo(object):
	#A class to encapsulate a video file that has been processed by birdBuddy
	#Contains functions to manipulate the video, get frames, process tracking objects found on in the database
	#about the file

	def __init__(self, db, path): #Load file info from the database and store it here in memory
		self.path = path
		self.db = db
		self.filenames = db.getSessionFiles(path) #A list of all files with this camera session
		#Use the database wrapper functions to send back the data
		self.sessionRunTime = db.getMotionProcessTime(path)
		self.sessionRecordTime = db.getSessionRecordtime(path)
		(self.original_width, self.original_height) = db.getOriginalDimensions(path) 
		self.frameCount = db.getTotalFrameCount(path)
		if self.sessionRunTime == 0: #It hasnt been processed, so abort
			self.TrackedList = None
			return #Let the calling function know theres no data
		(self.width, self.height) = db.getMotionPassWH(path)
		#Now we need a list of all trackedobject that existed in this video
		self.TrackedList = db.getTrackedObjects(path) #A list of Tracked
		#This outputs as a list of all trackedObjects, so lets 
		self.TrackingBoxes = {} #What gets passed to template to show tracking squares on the frames 
		#{Frame Index: {Tracking Object ID: (x,y,w,h)}}
		self.scale = self.original_width / self.width #What to multiply by to transform from the motion pass size to full size
		self.TrackingBoxes = TrackedActiveFrameList(self.TrackedList) #Get a simple list of frames that had activity, and their sqaures

		#Now make a list of all the High Res images for this file, for each frame saved
		#{FrameIndex: HR Image path}
		self.allHRImages = db.getAllHRImages(path)
		#Add in the list of user classified images associated with this video file
		self.userClassifications = db.getUserClassifications(self.path) #returns a pandas dataframe from the database
		activityCounts = []
		column_names=["Frame","Movement tracked","User Classifications"]
		for i in range(self.frameCount):
			try:
				trackingCount = len(self.TrackingBoxes[i])
			except Exception as e:
				trackingCount = 0
			try:
				classCount = len(self.addClassificationSamples)
			except Exception as e:
				classCount = 0
			if trackingCount ==0 and classCount == 0:
				continue
			else:
				t = [i,trackingCount,classCount]
				activityCounts.append(t)
		df=pd.DataFrame(activityCounts,columns=column_names)
		self.activityByFrame = df

	def getAllPossibles(self): #A dictionary classifier names and its possibility of existing in the image
		#[tracking ID]{ [classification: probability], [[classification2: prob2]...}
		return self.poss

	def getHRImagesByTO(self): #a list of paths of the high res images for each tracked object
		return self.HRImagesByTO
	
	def getTrackingBoxes(self): #What gets passed to template to show tracking sqaures on the frames
		#[tracking ID][frame Index][(x,y,w,h)]
		return self.TrackingBoxes

	def getAllHRImages(self):
		return self.allHRImages

	def getFrame(self, db, frameIndex):
		#Return a frame from the video file, load it from HR images if its saved already, otherwise load it from the video file
		hr = db.getAllHRImages(self.path) #A list of tuples [(frameindex, filename),...]
		try:
			imagePath = hr[frameIndex]
			frame = cv2.imread(imagePath)
			return(self.path, frame)
		except Exception as e:
			print("Loading frame {} from video file".format(frameIndex))
		#If nothing matched then we must create the HR image from the video file, and note in the database
		(videoPath, range) = db.getFrameImageFileName(self.path, frameIndex)
		self.fvs = FileVideoStream(videoPath).start()
		ret = self.fvs.more()
		frame = self.fvs.read() #Read in the next frame image
		frameCount = range[0]

		while ret is True or frame is not None:
			if frameIndex == frameCount:
				print("Returning frame " +  str(frameCount))
				saveFile = self.path + "frame" + str(frameCount) + ".jpg"
				cv2.imwrite(saveFile, frame) #save it to disk
				db.addHighResImage(self.path, frameIndex, saveFile, saveFile)
				return (self.path, frame)
			else:
				frameCount = frameCount + 1
			ret = self.fvs.more()
			frame = self.fvs.read()
		self.fvs.stop()
		return (self.path, frame)
	def getFrames(self, start, end): #Return a frame 
		#Return a frame from the video file, load it from HR images if its saved already, otherwise load it from the video file
		db = bbdb(Globals.get("DB"))
		hr = db.getAllHRImages(self.path) #A list of tuples [(frameindex, filename),...]
		try:
			imagePath = hr[frameIndex]
			frame = cv2.imread(imagePath)
			return(self.path, frame)
		except Exception as e:
			print("Loading frame {} from video file".format(frameIndex))
		#If nothing matched then we must create the HR image from the video file, and note in the database
		(videoPath, range) = db.getFrameImageFileName(self.path, frameIndex)
		self.fvs = FileVideoStream(videoPath).start()
		ret = self.fvs.more()
		frame = self.fvs.read() #Read in the next frame image
		frameCount = range[0]

		while ret is True or frame is not None:
			if frameIndex == frameCount:
				print("Returning frame " +  str(frameCount))
				saveFile = self.path + "frame" + str(frameCount) + ".jpg"
				cv2.imwrite(saveFile, frame) #save it to disk
				db.addHighResImage(self.path, frameIndex, saveFile, saveFile)
				return (self.path, frame)
			else:
				frameCount = frameCount + 1
			ret = self.fvs.more()
			frame = self.fvs.read()
		self.fvs.stop()
		return (self.path, frame)
	
	def getMotionPassWH(self):
		return (self.width, self.height)

	def __str__(self):
		if self.TrackedList is None:
			return "BB not run on {}.\nVideo has {} frames.".format(self.path, self.frameCount)
		trackedObjectCount = str(len(self.TrackedList))

		ret = "BBVideo object for " + self.path + "\n"
		ret = ret + "It has " + str(self.frameCount) + " frames and it tracked " + trackedObjectCount + " objects.\n"
		for index, to in enumerate(self.TrackedList):
			toid = str(to.ID)
			frame_start = str(to.frame_start)
			frame_end = str(to.frame_end)
			total_frame = str(to.frame_end - to.frame_start)
			ret = ret + "Tracked Object " + toid + " runs from frame " + frame_start + " to " + frame_end + "("+total_frame+ ").\n"
		totalActiveFrames = str(len(self.TrackingBoxes))
		ret = ret + totalActiveFrames + " frames had movement.\n"
		#{frameindex1:{tracking object ID: square}}
		#Print out the frames and their active tracking squares
		for key, value in self.TrackingBoxes.items(): #Print it back out see if it makes sense
			index = str(key)
			activeSquares = str(len(value))
			ret = ret + "Index: " + index + ". Has " + activeSquares + " active tracking squares.\n"
			#Now loop through every item in the inner dictionary to display the trackin object id and its square
			for k, v in value.items():
				toid = str(k)
				square = str(v)
				ret = ret + "		Tracking Object ID: " + toid + ". Square: " + square + "\n"
		return ret

	def getCroppedImageB64(self, db, frameIndex, x,y,w,h):
		path = self.hrSavePath + self.getHRImagePath(db, frameIndex) #Return the path of the full res image file for this frame
		img = Image.open(path)
		crop = (x,y,x+w,y+h)
		img = img.crop(crop)
		b = BytesIO()
		img.save(b, 'jpeg')
		im_bytes = b.getvalue()

		b64 = base64.b64encode(im_bytes).decode()
		b64 = '<img src="data:image/jpg;base64,{}'.format(b64)
		b64 = b64 + '"/>'
		return b64

	def getCroppedImageBinary(self, db, frameIndex, x,y,w,h):
		path = self.hrSavePath + self.getHRImagePath(db, frameIndex) #Return the path of the full res image file for this frame
		img = Image.open(path)
		crop = (x,y,x+w,y+h)
		img = img.crop(crop)
		b = BytesIO()
		img.save(b, 'jpeg')
		im_bytes = b.getvalue()
		return im_bytes

	def addClassificationSample(self,db,frameIndex,x,y,w,h,classification,image):
		#Add the supplied cropped image to the database as a classifier
		db.addClassification(self.path,frameIndex,x,y,w,h,classification,image)

	def getUserClassifications(self, db):
		#Retrieve the list of classifications the user identified
		#Add in the list of user classified images associated with this video file
		self.userClassifications = db.getUserClassifications(self.path) #returns a pandas dataframe from the database
		return self.userClassifications
	
	def drawTrackingBoxes(self, frame, frameindex):
		try:
			boxes = self.TrackingBoxes[frameindex]
		except Exception as e:
			#Theres no activity here
			return frame

		for (TrackingObjectID, rect) in boxes.items():
			x = int(rect[0])
			y = int(rect[1])
			w = int(rect[2])
			h = int(rect[3])
			start = (x, y) #Take the 4 points x y w h and make it rectangles for openbcv
			end = (x+w,y+h)
			cv2.rectangle(frame, start, end, (255, 255, 255), 2)
			cv2.putText(frame,str(TrackingObjectID),(x, y),cv2.FONT_HERSHEY_SIMPLEX,0.5,(255, 255, 255),2)
		return frame
