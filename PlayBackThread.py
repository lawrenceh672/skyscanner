import threading
from parameters import Parameters
from SkyScanner_DB import bbdb
from imutils.video import FileVideoStream
from Globals import Globals
import cv2
import time
import datetime
stopWatchStartTime = 0
def stopWatchStart():
	global stopWatchStartTime
	curr_dt = datetime.datetime.now()
	stopWatchStartTime = curr_dt.timestamp()
def stopWatchStop():
	global stopWatchStartTime
	curr_dt = datetime.datetime.now()
	stopWatchEndTime = curr_dt.timestamp()
	return stopWatchEndTime - stopWatchStartTime

class PlayBackThread(workerThread):
	def __init__(self, *args, **kwargs):
		super(PlayBackThread, self).__init__("Playback Thread {}".format(args[0]), **kwargs)
		self._stop = threading.Event()
		self.P.set("Session", args[0])
		self.P.set("DB File Name", args[1])
		self.P.set("Total Frames", 0)
		self.files = [] #a list of video files
		self.totalFrames = 0
		self.frameIndex = 0
		self.name = "Playback Thread {}".format(self.P.get("Session"))
		self.outputVisual = True
		#self.P.set("outputImage", "No image loaded")
		self.P.updated = False #We've processed these parameter updates

	def __str__(self):
		return self.name

	def stop(self):
		super(PlayBackThread, self).stop()
		self._stop.set()
		self.outputVisual = False
 
	def stopped(self):
		return self._stop.isSet()

	def run(self):
		P = self.P
		path = P.get("Session")
		db = bbdb(P.get("DB File Name"))
		#get the list of video files from this session and play them into a window
		files = db.getSessionFiles(path) #Now we have a list of video files, lets play the video files in sequence
		self.totalFrames = db.getTotalFrameCount(path)
		frameIndex = 0
		stopWatchStart()
		frametime = stopWatchStop()
		for f in files:
			P.set("Frame", frameIndex)
			P.set("File", f)
			fvs = FileVideoStream(f).start()
			#Start the video loop
			ret = fvs.more()
			frame = fvs.read() #Read in the next frame image
			frameIndex = 0
			while ret is True:
				stopWatchStart()
				if frame is not None:
					#cv2.imshow(windowTitle, frame)
					#cv2.waitKey(1)
					if self.outputVisual:
						self.P.set("outputImage", frame) #Set an output image for other threads to display as needed
						#frametime = stopWatchStop()
						#time.sleep(max(0.3, 1 - frametime))
						#cv2.imshow("Sky Scanner Playback", frame)
						#cv2.waitKey(1)
					else:
						self.P.set("outputImage", None)
					frameIndex += 1
					self.P.set("Frame Recorded", frameIndex)
				ret = fvs.more()
				if ret is False:
					break
				frame = fvs.read() #Read in the next frame image
			#After looping video frames, kill the window
			#cv2.destroyWindow("Sky Scanner Playback")
		self.stop()
		print("End of files")

	def read(self): #Gets the next frame from the camera session
		#First lets check if we're waiting on it
		while self.P.updated == False and self.stopped() == False:
			time.sleep(0.05)

		#Now we're either stopped or the parameters have updated
		if self.stopped(): #Nothing to read if the thread is off
			return None
		
		#Otherwise get the frame from outputimage parameter
		if self.P.isUpdated("outputImage"):
			ret = self.P.get("outputImage")
			return ret