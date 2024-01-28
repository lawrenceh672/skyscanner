# import the necessary packages
from imutils.video import VideoStream
from imutils.video import FileVideoStream
from imutils.video import FPS
import imutils
import cv2
from Tracked import Tracked
import numpy as np
from SkyScanner_DB import bbdb
#from PIL import Image
#from flask import Flask, request, session, render_template
from BBVideo import BBVideo
import threading
from Globals import Globals
from workerthreads import workerThread
from PIL import Image


class BBProcessingThread(workerThread):
	def __init__(self, *args, **kwargs):
		super(BBProcessingThread, self).__init__(args[0], **kwargs)
		self._stop = threading.Event()
		self.files = [] #a list of video files
		self.totalFrames = 0
		self.frameIndex = 0
		self.BB = None #The birdbuddy object used to process this camera session
		self.outputVisual = True
		self.P.set("outputImage", "No image available")
		#check the name its wrong

	def __str__(self):
		ret = str(self.P)
		return ret
	# function using _stop function
	def stop(self):
		super(BBProcessingThread, self).stop()
		self.outputVisual = False
		self._stop.set()
 
	def stopped(self):
		return self._stop.isSet()

	def run(self):
		dbFileName = Globals.get("DB")
		db = bbdb(dbFileName)
		currentSession = Globals.get("Camera Session")
		BBScale = 100
		MinArea = 25
		inputt = Globals.get("inputt")
		bbv = Globals.get("BB Video Results")

		files = db.getSessionFiles(currentSession) #Now we have a list of video files, lets play the video files in sequence
		self.BB = BirdBuddy(dbFileName, currentSession, BBScale, MinArea, self.outputVisual)
		for f in files:
			#Start processing the first file
			self.BB.startFileProcessing(f,db)
			self.P.set("Reading File", f)
			
			while self.BB.process(db):
				self.P.set("Frame Index", "Frame {} of {}".format(self.BB.frame_count, bbv.frameCount))
				self.P.set("outputImage", self.BB.outputImage)

		self.BB.finish(db) #Write out all remaining data and close up the window
		#Remake the bbv object to summarize the output of BB from its database records
		bbv = BBVideo(db, currentSession)
		Globals.set("BB Video Results", bbv)
		self.stop()

class BirdBuddy:
	def __init__(self, dbFileName, save_path, scale, minArea, outputVisual):
		self.save_path = save_path
		#initialize the first frame in the video streamsave
		self.firstFrame = None #trigger some initialization
		self.minArea = minArea
		self.frame_count = 0
		self.outputVisual = outputVisual #Whether or not to waste time drawing it
		self.Take_Screen_Grab = True #we dont have our base screen grab now
		self.TrackedList = [] #all objects being tracked
		self.TrackedCount = 0 #Count each tracker added
		self.StatusChange = False #Weve added or completed an object track
		Tracked.ID = 0 #Reset the tracked counter
		self.scale = scale
		self.status = "Session {} processing started".format(save_path)
		print("Activating BB session {}".format(save_path))

		self.displayOn = False #True if outputting an image file
		self.outputFrame = None


	def startFileProcessing(self, path, db):
		self.path = path
		self.vs = cv2.VideoCapture(self.path)
		self.total_frames = int(self.vs.get(cv2.CAP_PROP_FRAME_COUNT)) #The total number of frames in the video
		self.original_frame_width = self.vs.get(3)
		self.original_frame_height = self.vs.get(4)
		self.video_width = round(self.original_frame_width * (self.scale/100))
		self.video_height = round(self.original_frame_height * (self.scale/100))
		#Establish the ratio of the size of the original frame to the resized one to be processed
		self.x_transform = self.scale
		self.y_transform = self.scale
		# start the file video stream thread and allow the buffer to
		# start to fill
		self.fvs = FileVideoStream(self.path).start()
		# start the FPS timer
		self.fps = FPS().start()
		#add it to the database of processed files, update the existing entry that was added when the file was uploaded
		#to the server
		db.updateFileProcessParameters(self.path, self.video_width, self.video_height)
		db.resetFile(self.path) #remove previous processing information from here and start over if necessary
		self.finished = False #Will be true once the processing thread executes self.finish

	def transformImageCoordinates(self, x, y, w, h): #Resize the coordinates match the full size image, not the smaller processing 
		(xNew, yNew, wNew, hNew) = (int(x * self.x_transform), 
							  int(y * self.y_transform), 
							  int(w * self.x_transform), 
							  int(h * self.y_transform))
		return (xNew, yNew, wNew, hNew)

	def closeEnough(self, x, y, w, h):
		#
		#Determine which tracking object this new rectangle belongs to, check if the bottom left coord is in the 
		#existing tracking rectangle.
		for o in self.TrackedList:
			# Area of 1st Rectangle
			#	   ######################### (o.x+o.w,o.y+o.h)				
			#	   #Current Tracked 		#							
			#	   #Object					#							
			#	   #				##################### (x+w,y+h)	
			#		#				#		#			#				
			#		#########################			#				
			#		(o.x,o.y)		#					#incoming motion
			#						#capture 			#				
			#						#rectangle			#				
			#						#####################				
			#						(x,y)

			#Any corner of the incoming rectangle thats in the current tracked object will qualify as being "close enough"
			#Therefore if the intersection area is more than zero it can qualify
			(ox,oy,ow,oh) = o.lastSquare()
			rect1 = {
				"left": ox,
				"right": ox + ow,
				"top": oy,
				"bottom" : oy + oh,
			}
			rect2 = {
				"left": x,
				"right": x + w,
				"top": y,
				"bottom": y + h,
			}
			x_overlap = max(0, min(rect1["right"], rect2["right"]) - max(rect1["left"], rect2["left"]))
			y_overlap = max(0, min(rect1["bottom"], rect2["bottom"]) - max(rect1["top"], rect2["top"]))
			overlapArea = x_overlap * y_overlap;
			#if either point of the incoming rectangle is in the first rectangle, merge the two rectangles
			#and return the index of the adjusted tracked object
			if overlapArea > 0: #Its got some intersection
				return o

		return None  #Gone through list nothing matched well enough

	def process(self, db):
		if(self.vs.isOpened() == False): #If the camera is off or at the end of the file, this should break the loop
			print("Ended birdbuddy processing stage. Saving to the database.")
			return False

		# start reading the frames and initialize the screen
		ret = self.fvs.more()
		frame = self.fvs.read() #Read in the next frame image

		# if the frame could not be grabbed, then we have reached the end
		# of the video
		if ret is False or frame is None:
			# stop the timer and display FPS information
			self.fps.stop()
			#print("[INFO] elasped time: {:.2f}".format(self.fps.elapsed()))
			#print("[INFO] approx. FPS: {:.2f}".format(self.fps.fps()))
			self.fvs.stop()
			return False

		self.frame_count = self.frame_count + 1 #Count the frames for later use

		#Start processing the frame to compare it for motion, by resizing it to a smaller resolution
		current_frame = imutils.resize(frame, width=self.video_width)

		# if the first frame is None, initialize it,, or if theres been no noticeable activity so start the comparison frame her
		#  or every 50 frames no matter what
		if (self.firstFrame is None) or self.Take_Screen_Grab == True or self.frame_count % 50 == 0:
			self.firstFrame = frame
			self.first_gray = imutils.resize(self.firstFrame, width=self.video_width)
			self.first_gray = cv2.cvtColor(self.first_gray, cv2.COLOR_BGR2GRAY)
			self.first_gray = cv2.GaussianBlur(self.first_gray, (21, 21), 0)
			self.Take_Screen_Grab = False #shouldnt need to keep taking over and over just in case
			#(flag, encodedImage) = cv2.imencode(".jpg", current_frame)
			#self.outputImage = encodedImage.tobytes()
			self.outputImage = Image.fromarray(current_frame)
			return True	#Loop to the next frame comparing against this current one
		
		# compute the absolute difference between the current frame and first frame to compare it against
		gray_frame = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
		gray_frame = cv2.GaussianBlur(gray_frame, (21, 21), 0)
		frameDelta = cv2.absdiff(self.first_gray, gray_frame)
		thresh = cv2.threshold(frameDelta, 25, 255, cv2.THRESH_BINARY)[1]

		# dilate the thresholded image to fill in holes, then find contours
		# on thresholded image
		thresh = cv2.dilate(thresh, None, iterations=2)
		cnts = cv2.findContours(thresh.copy(), 
								cv2.RETR_EXTERNAL,
								cv2.CHAIN_APPROX_SIMPLE)
		cnts = imutils.grab_contours(cnts)
		
		for c in cnts:
			# if the contour is too small, ignore it
			if cv2.contourArea(c) < self.minArea:
				continue
			(x, y, w, h) = cv2.boundingRect(c)
			#is this an existing Tracked being tracked?
			#compare the rectangle to existing Tracked rectangels
			#if its close enough extend the time sequence on the existing pbject
			#if not make another tracking rectangle
			#if it occupies 95% of the same area then its same enough
			#compare the intersection of the two bounding rectangles
			#if theres no Trackeds to contain it, make a new Tracked and insert it into the lists
			o = self.closeEnough(x, y, w, h)
			if(o is not None):
				o.classification == None  #TODO:  We dont have classifiers yet											
				#Note this tracked object as being active
				o.active = True
				o.frame_end = self.frame_count
				(ox, oy, ow, oh) = o.lastSquare() #Get the last square of the tracked object

				#good to know the path it took
				#Now that one corner is in the current tracked object, resize the tracked object to encompass both objects
				newLeftX = min(ox,x)
				newLeftY = min(oy,y)
				newRightX = max(x+w,ox+ow)
				newRightY = max(y+h,oy+oh)
				newWidth = newRightX - newLeftX
				newHeight = newRightY - newLeftY
				track = (newLeftX, newLeftY, newWidth, newHeight) #Get the last square this tracking object went through
				o.xywh_track.append(track)
			else: #Else we create a new tracked object and append it to the other ones being tracked currently
				#img = current_frame[y:y+h, x:x+w]
				#is_success, im_buf_arr = cv2.imencode(".jpg", img)
				#byte_im = im_buf_arr.tobytes()
				o = Tracked(self.frame_count) #reset the Tracked as active
				track = (x, y, w, h)
				o.addTrackingSquare(track)
				self.TrackedList.append(o)
				self.StatusChange = True #showing a new tracking object has entered
				self.TrackedCount += 1
			if self.outputVisual:
				#Draw the contour found
				cv2.rectangle(current_frame, o.RectPointOne(), o.RectPointTwo(), (255, 255, 255), 2)
				cv2.putText(current_frame,str(o.ID),(x, y),cv2.FONT_HERSHEY_SIMPLEX,0.5,(255, 255, 255),2)	
			#Finished counting contours now to process them a little further
		#remove all inactive all tracked objects that werent touched during the last loop
		temp = [] #Temp list to store tracked objects that arent being removed
		while self.TrackedList:
			o = self.TrackedList.pop()
			if o.active == False: #This tracking object is done, save it to the db and remove it from the list
				#Output to the database
				db.addTrackedObject(self.path, o)
				self.StatusChange = True
				continue
			temp.append(o) #Put it back in if its active
			o.active = False #Reset it so it'll have to see motion to reactive the tracking rectangle.
		self.TrackedList = temp #Reassign the list without the inactive tracking objects

		#If theres been nothing additional tracked, or anything removed, 
		if len(self.TrackedList) == 0: #nothing is being currently tracked
			self.Take_Screen_Grab = True #and lets use this opportunity to update the screen, as there is now no more appreciable movement
		
		if self.StatusChange == True: #Something was added or removed, so save the frame for later identification
			saveFile = self.save_path + "frame" + str(self.frame_count) + ".jpg"
			cv2.imwrite(saveFile, frame) #save it to disk
			#Output the high res image information to the database
			db.addHighResImage(self.save_path, self.frame_count, saveFile, saveFile)
			self.StatusChange = False


		#End the Tracked Object processing loop, output the final image with tracking object rectangles
		if self.outputVisual:
			output = Image.fromarray(current_frame)
			self.outputImage = output #Output the frame with the tracking squares on it
		else:
			self.outputImage = str(self.frame_count)
		return self.outputImage
	
	def finish(self, db):
		#Output any tracked objects still being tracked at end of video file
		while self.TrackedList:
			o = self.TrackedList.pop()
			db.addTrackedObject(self.path, o)
			print("Finished tracking square {}".format(o))
		self.fvs.stop()
		self.finished = True
		self.status = "off"

#After processing the video, we have a database of all the motion detected by the algorithm
#In this stage it'll output an html file where we can edit, add and remove classifications for each image
#The above program has outputted many screen shot where any motion is detected numbered by frame from its video
#The website will display a list of thumbnails with a drop down for classification and textbox for adding one
#deletion wont be necessary to start
#As it gets better itll assign probabilities for classifications for each image aiding in selection
#If the user clicks on the thumbnail, it'll display the matching frame with the tracked object detected in full resolution.
#to let the user see the whole area in case it needs a context clue for the user to figure it out
