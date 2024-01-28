import datetime
import os
import cv2
import threading
from SkyScanner_DB import bbdb
from workerthreads import workerThread
from Globals import threads, Globals

def sanitizePath(value):
	deletechars = '\/:*?"<>|. '
	value = str(value)
	for c in deletechars:
		value = value.replace(c,'')
	return value

def numberToAlphabetical(num):
	convert={0:"0", 1:"a",2:"b",3:"c",4:"d",5:"e",6:"f",7:"g",8:"h",9:"i",10:"j",11:"k",12:"l",13:"m",14:"n",15:"o",16:"p",17:"q",18:"r",
			19:"s",20:"t",21:"u",22:"v",23:"w",24:"x",25:"y",26:"z"}
	#To maintain alphabetical order, set the total string width as 8, and fill in it with zeros
	base_num = ""
	base = 26
	column = 0
	while num>0 or column < 8:
		dig = int(num%base)
		base_num += convert[dig]  #Using uppercase letters
		num //= base
		column +=1
	base_num = base_num[::-1]  #To reverse the string
	return base_num


class CameraThread(workerThread):
	#A thread class to take in and store a video feed, splitting it up into regular sized file chunks
	def __init__(self, *args, **kwargs):
		super(CameraThread, self).__init__(args[2], **kwargs)
		self.name = args[2] #Gotta get the name in there at the beginning
		self._stop = threading.Event()
		self.camera = args[0]
		self.dbFileName = args[1]
		self.saved = False #Becomes true when the the thread has shut down the camera and saved to the db
 
	def __str__(self):
		ret = "Camera: {} @ {} using DB {}. ".format(self.camera.name, self.camera.startTime, self.dbFileName)
		return ret
	# function using _stop function
	def stop(self):
		self._stop.set()
		self.outputVisual = False
 
	def stopped(self):
		return self._stop.isSet()

	def run(self): #Sent a camera object to get the relevant information from
		db = bbdb("bbdb.db")
		camera = self.camera #Start the camera thread with the camera set from the user
		#Add it into the database as a running camera
		filename = camera.Outputfile() #Start saving the output files
		if camera.name == 'WEBCAM':
			cap = cv2.VideoCapture(0)
		else:
			cap = cv2.VideoCapture(camera.URL) #Lets try to open the rtsp camera or its a file path
			
		camera.frame_width = int(cap.get(3))
		camera.frame_height = int(cap.get(4))
		db.addCameraFeed(camera) #Enter this camera session into the database

		#Setup the saved file output path
		vid_cod = cv2.VideoWriter_fourcc(*'mp4v')
		output = cv2.VideoWriter(filename, vid_cod, 20.0, (camera.frame_width,camera.frame_height))
		self.outputVisual = True
		while camera.isRunning == True: #Looping until the threads stop function is called and the camera shut down
			#Read in the frame from the camera
			ret, frame = cap.read()
			if ret is True: #process the frame from the camera
				#cv2.imshow(camera.name,frame)
				#cv2.waitKey(1)
				self.P.set("outputImage", frame)
				output.write(frame)
				camera.frame_count += 1

				if camera.frame_count % camera.framesPerFile == 0:
					output.release() #Write out the file name
					db.addFile(filename)
					#Update the camera session
					db.updateCameraSession(camera)

					#Start making a new file
					filename = camera.Outputfile()
					#open the next file
					output = cv2.VideoWriter(filename, vid_cod, 20.0, (camera.frame_width,camera.frame_height))
			else:
				output.release()
				print("No input from camera {}".format(camera))
				break
		output.release()
		self.stop()

class Camera(object):
    #A class to hold camera information from the database and handle operations until it is stored back into the database
	def __init__(self):
		self.isRunning = False
		self.URL = "rtsp://larry:garbledun@192.168.219.7:554/h265Preview_01_main"
		self.framesRecorded = 0 #If isrunning is false and framesrecorded is zero it can start
		self.name = "ReoLink"
		self.framesPerFile = 8192
		self.RootPath = "d:\\cameraupload\\"
		self.filesCreated = 0 #how many files have been created during the active session
		self.startTime = None
		self.frame_width = 640
		self.frame_height = 480
		self.frame_count = 0
		self.fullPath = None
		self.ct = None #A thread to run the camera and store the video captures

	def Outputfile(self): #return a string of the full path that will be used based on the session and file count
		#root\camera name\start time\x.mp4
		file = "{}.mp4".format(numberToAlphabetical(int(self.frame_count/self.framesPerFile)))
		ret = self.fullPath + file
		return ret

	def __str__(self):
		ret = "Camera: {} @ {}. Active:{}[{}]".format(self.name, self.URL,self.isRunning,self.frame_count)
		return ret
		
	def Load_Video_File(self, path):
		self.name = "FILE"
		self.URL = path

	def toggleOnOff(self, dbFileName):
		try:
			if self.isRunning:
				self.ct.stop() #Flag the thread to stop and then finish the recording session and close the viewing window
				#Finish up the recording and set the camera to inactive status
				filename = self.Outputfile() #Get the current file based on the cameras frame count
				self.isRunning = False
				#Finish off the last part of this video file and save it
				db = bbdb(dbFileName)
				db.addFile(filename)
				db.updateCameraSession(self) #Make the db reflect the camera session is over and finalize the values
				db.closeAndCommit()
				print("Closing camera window {}".format(self.name))
				#cv2.destroyWindow(self.name)
				self.saved = True #Flag
				self.frame_count = 0 #Reset the cameras settings for another session
				threads.delete(self.ct.name, None)#The camera thread is off
			else:
				self.isRunning = True
				curr_dt = datetime.datetime.now()
				self.startTime = int(round(curr_dt.timestamp()))
				#Create the directory to store the files
				time = sanitizePath(self.startTime)
				self.fullPath = "{}{}\\{}\\".format(self.RootPath, self.name, time)
				try:
					os.makedirs(self.fullPath)
				except Exception as e:
					print(e)
				#Now start the thread
				name = "{} recording {}".format(self.name, time)
				self.ct = CameraThread(self, dbFileName, name)
				print("Activating camera sessions {}".format(self.ct))
				self.ct.start()
				threads.set(self.ct.name, self.ct) #Add the camera thread to the list of running threads
		except Exception as e:
			print("Error toggling Camera {}. {}".format(self, e))
			self.isRunning = False

		return self.isRunning #Return the toggled boolean

	def shutDown(self): #Turn off the camera and finish any recording session
		if self.isRunning:
			self.ct.stop()
			self.isRunning = False