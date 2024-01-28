#Start the camera
#Open database, start saving video files and use the db to access records
#Set photo interval time, save high res files to jpg and record in db
#Open command line interface, windows to show photos and videos but all interface on text
import cv2
from BirdBuddy import *
from cameras import Camera
from DBThread import DB
from BBVideo import *
from Inputt import *
import math
from parameters import Parameters
from workerthreads import *
from Classifier import Classifier  #Handles the classifier selection, retrieval and storing to DB
from Globals import Globals
import matplotlib.pyplot as plt
import matplotlib
from PIL import Image
import datetime
import pandas as pd
import os

#Set the global variables inside one global variable called Globals
try:
	inputt = Inputt()
	Globals.set("inputt",inputt) #The interface =

	dbFileName = "bbdb.db"
	db = bbdb(dbFileName) #Create the container class for the birdbuddy database
	Globals.set("DB", dbFileName) #"The database connection"

	currentSession = db.getNewestSessionPath() #A global variable to see what session were working on, the path to its saved files the key to the database
	Globals.set("Camera Session", currentSession) #The camera session file path

	bb = None #A BirdBuddy Object to handle motion tracking
	Globals.set("BirdBuddy", bb) #"The movement tracking algorithm, saved to the database"

	bbv = BBVideo(db, currentSession)  #Hold the tracking information from a BB processed video in memory
	Globals.set("BB Video Results", bbv) #BirdBuddy results database to python object for analysis

	classifier = Classifier("test") #A Classifier object to hold samples and generate classifiers, and to run the classifier on other sessions
	Globals.set("Classifier", classifier) #The classification sample extractor and analyzer object for the current classification under use

	Root_Path = "d:\\cameraupload\\" #Base directory for all files
	Globals.set("Root Path", Root_Path)

	#Start the camera selection list
	cameras = []
	#add the webcam
	c = Camera()
	c.name = 'WEBCAM'
	cameras.append(c)
	#Add cameras from the database
	df = db.getListofCameras()
	for row in df.itertuples():
		c = Camera()
		c.name = row.NAME
		c.URL = row.RTSP_URL
		cameras.append(c)
	Globals.set("Cameras", cameras)
except Exception as e:
	print(f"Globals failed exception {e}")
	print(f"inputt {Globals}")

#define the functions to link to a menu option
#TODO add a file transfer speed utility
"""
1. Camera
"""
def toggleCamera(): #1
	#Get the user to select the camera to turn on
	#format the text string 0. Webcam [ON/OFF]
	cams = {}
	for c in cameras:
		if c.isRunning:
			menuOption = "{} [ON]".format(c.name)
		else:
			menuOption = "{} [OFF]".format(c.name)
		cams[c] = menuOption

	camera = inputt.enumerateAndSelect(cameras) #add the cameras list as a menu selection
	if camera:
		camera = camera[0]
		camera.toggleOnOff(dbFileName)
	else:
		return["No camera selected."]

	return [str(camera)]
"""
2. Database
"""
def root2(): #2
	return ["Currently connected to database:\n{}".format(dbFileName)]
def resetDB(): #2.1
	confirmation = inputt.confirmAction("delete database")
	if confirmation:
		print("Deleting {}".format(dbFileName))
		db.runScript("createdb.sql")
def switchDB(): #2.2
	inputt.getFileName("bbdb.db")
	dbFileName = inputt.nextLine()
	db = bbdb(dbFileName)
	
"""
3. Status
"""
def root3(): #3
	return ["display the values of running threads and Globals."]
def globalsStatus(): #3.1
	selection = inputt.enumerateAndSelect(Globals)
	ret = [str(selection)]
	return ret
def threadsStatus(): #3.2 
	#
	#Update this to dynamically update the menu on the threads progress as reported by the thread
	#
	selection = inputt.enumerateAndSelect(threads)
	ret = [str(selection)]
	return ret
"""
4. Camera Session
"""
def root4(): #4
	return ["Camera session {} currently loaded".format(currentSession)]
def selectCameraSession(): #4.1
	global currentSession
	global bbv,bb

	df = db.getSessions()
	ret = []
	sessions = []
	for row in df.itertuples():
		sessions.append(row.PATH)
	userInput = inputt.enumerateAndSelect(sessions) #add the cameras list as a menu selection and get the users selection
	if userInput:
		currentSession = userInput[0] #Get the path for the camera session, enumerate returns an output list of one string
		Globals.set("Camera Session", currentSession)
		ret.append("Session {} selected".format(currentSession))
	else:
		print("No camera session selected, reverting to original")

	status() #New session update context sensitive menu info
	#Start loading the BBvideo object
	try:
		#Determine when the session as ran, or not
		sessionRunTime = db.getMotionProcessTime(currentSession)
		bb = None #Delete the previous birdbuddy object
		bbv = BBVideo(db, currentSession) #Load the BB process information into global BBV
		if sessionRunTime == 0:
			ret.append("Loaded video information, BB has not been run this session")
		else:
			ret.append("Loaded video information. BBV ran on {}".format(sessionRunTime))
	except Exception as e:
		ret.append("Error loading BBVideo: {}".format(e))
		bbv = None
	return ret
def deleteCameraSession(): #4.2 Delete the currently selected camera session 
	ret = "Delete session {}?\n".format(currentSession)
	ret += "Session recorded on {}\n".format(bbv.sessionRecordTime)
	ret += "Frame count {}\n".format(bbv.frameCount)
	ret += "Press y to delete, any other key to cancel"
	ret = [ret]
	return ret	
def playBack(): #4.3 Play back the current session
	if currentSession == None or dbFileName == None:
		return False
	thread = PlayBackThread(currentSession, dbFileName)
	thread.start()
	thread.P.set("Visualization menu level", inputt.menuLevel)
	return ["Playing back {}".format(currentSession)]
def confirmDeleteCameraSession(): #4.2.y
	db.deleteSession(currentSession)
	ret = ["Session {} deleted".format(currentSession)]
	return ret
def Load_Video_File(): #4.4
	#Add the video file to the list
	filename = inputt.getFileName(None, ext = "mp4")
	camera = Camera()
	camera.Load_Video_File(filename) #T up the the video file
	camera.toggleOnOff(dbFileName)
	return ["Entering File {}".format(filename)]
"""
5. BirdBuddy 
"""
def root5(): #5
	return ["Use visualization to identify frames of interest","Run BB process to mark areas of high movement"]
def bbvDataViz(): #5.1
	# Scatter plot showing tracking activity vs frame index, help the user pick a frame to start looking from
	df = bbv.activityByFrame
	ret = ""
	try:
		df.plot(x ='Frame', y='Movement tracked', kind = 'bar')
	except: #Probably no data
		ret += "No data to plot"

	#plt.ion()
	matplotlib.rcParams['interactive'] == True
	plt.title("BBV")
	plt.show() #Let the user scan the tracked data and get frames to investigate
	inputt.goUpOneLevel() #Theres no further options here, jump back to the calling menu
	return [ret]
def BBProcess(): #5.2
	#get the list of video files from this session and run BirdBuddy on them
	#TO threadify it so the user can get back to the menu
	#put the while loop in birdbuddy, just use the path not the file name
	#Start the function and let it update inputt as to its status
	#Remove the status function
	#update session run time show if its done processing, or is in the process thereof

	#Need to get the backend setup windows only does qtagg, tried setting environment variable
	try:
		thread = BBProcessingThread("BB Thread {}".format(currentSession))
		thread.start()
	except Exception as e:
		print("Exception during BBProcess {}".format(e))
	ret = ["BB processing started on {}".format(currentSession)]
	return ret
"""
6 User Classification
"""
def root6(): #6
	return ["This is the menu where you can select classification samples from the current session\nYou can run the classification compiler as you develop you classifier."]
def selectClassifierSample(): #6.1
	db = bbdb(dbFileName = Globals.get("DB"))
	if currentSession == None: #Prompt the user to pick a camera session
		inputt.prompt("Pick a camera session")
		inputt.menuLevel = ['4','1']
		return
	if bbv == None: #No camera session has been BB processed
		inputt.prompt("BB process the video")
		inputt.menuLevel = ['4','4']
		return
	#display the current frame 
	classifier.frame = bbv.getFrame(db, classifier.frameIndex)[1] #The first one is the file path
	return [classifier.frame]
def classifierJumpToFrame(): #6.1.1
	classifier.frameIndex = inputt.getInteger("Select Frame", 0, bbv.frameCount, 0)
	classifier.frame = bbv.getFrame(db, classifier.frameIndex)[1] #The first one is the file path
	inputt.goUpOneLevel() #Works nicer if it goes back up to display the frame selection options
	return [classifier.frame]
def classifierGoDownOneFrame(): #6.1.<-
	classifier.frameIndex -= 1
	if classifier.frameIndex < 0:
		classifier.frameIndex = 0
	classifier.frame = bbv.getFrame(db, classifier.frameIndex)[1] #The first one is the file path
	inputt.goUpOneLevel() #Works nicer if it goes back up to display the frame selection options
	return [classifier.frame]
def classifierGoUpOneFrame(): #6.1.->
	classifier.frameIndex += 1
	if classifier.frameIndex > bbv.frameCount:
		classifier.frameIndex = bbv.frameCount
	classifier.frame = bbv.getFrame(db, classifier.frameIndex)[1] #The first one is the file path
	inputt.goUpOneLevel() #Works nicer if it goes back up to display the frame selection options
	return [classifier.frame]
def selectROI(): #6.1.k
	sel = cv2.selectROI("Select ROI", classifier.frame)
	# Crop image
	imCrop = classifier.frame[int(sel[1]):int(sel[1]+sel[3]), int(sel[0]):int(sel[0]+sel[2])]
	cv2.destroyWindow("Select ROI")
	#Put the selected image up on the big board
	return [imCrop,"User Selection",sel] #Need to push this down one more menu level keep selections in the auto inputt loop
def acceptROI(): #6.1.k.a Enter the ROI into the database
	lastOutput = inputt.functionReturn #Get the output from the last function, for the selection square
	sel = lastOutput[2]
	imCrop = lastOutput[0]
	name = inputt.getString("Enter name for the ROI")
	bbv.addClassificationSample(db, classifier.frameIndex, sel[0],sel[1],sel[2], sel[3], name, imCrop)
	#put the frame selector window back up and add the classification to the internal list
	x2=sel[1]+sel[3]
	y2=sel[0]+sel[2]
	x1=sel[1]
	y1=sel[0]
	coords = ((x1,y1),(x2,y2))
	inputt.prompt("Classification {} at frame {}, @ {} entered in DB {}".format(name, classifier.frameIndex, coords, Globals.get("DB")))
	inputt.goUpOneLevel() #Back it up to the frame selection area, presumably only one sample per frame but if not can go back in
	inputt.goUpOneLevel() #Back it up to the frame selection area, presumably only one sample per frame but if not can go back in
	inputt.goUpOneLevel() #Back it up to the frame selection area, presumably only one sample per frame but if not can go back in
	classifier.load(classifier.name) #Reload the classifier sample information
	return ["{}".format(classifier)] 
def loadClassificationSamples(): #6.2
	#First get all the samples for the current classifier and display them with thumbnails
	#Later update it to scroll through what must be 100s of samples after a while
	ret = []
	#Cut out some of the information from the db
	reti = {} #
	originals = {}
	dictionaryKey = None
	for key,val in classifier.samples.items(): #Make the list of images without the identifying info, depend on the pic only
		#get the size
		size = val.size
		text = "{}x{} @ ({},{})".format(size[0],size[1],key[2],key[3],key[4],key[5])
		maxSize = (38,38)
		thumb = val.copy()
		thumb.thumbnail(maxSize)
		#Thumbnail the images
		reti.update({text:thumb})
		originals.update({text:val}) #Save the original

	selection = inputt.enumerateAndSelect(reti)

	#Its returned the thumbnail from the dictionary, now to get the original sized pic and output it

	if selection:
		for key,val in reti.items(): #Make the list of images without the identifying info, depend on the pic only
			#get the size
			if selection[0] == key: #this thumbnail matches
				#return the original sized image
				original = originals[key]
				ret.append("Delete this classifier sample?")
				ret.append(original)
	else:
		ret.append("No classifer selected, reverting to {}".format(classifier.name))
	#Get the image from the initial dictionary to return as a full size image into the output pane
	
	return ret
def deleteClassificationSample(): #6.2.list
	#Confirm the user wants to delete the image they selected before
	selection = inputt.functionReturn #A list with one selected image from the above menu
	if inputt.confirmAction("this sample image for the classifier {}".format(classifier.name)):
		return ["Deleted", selection, "From classifier {}".format(classifier.name)]
	else:
		return ["Action cancelled, sample NOT deleted"]
def deleteClassification(): #6.3
	print("Load classification sample")
	selection = inputt.enumerateAndSelect(classifier.classes) #Select the classification
	key = inputt.anyKey("Press d to delete, any other key to cancel")
	if key == 'd':
		classifier.deleteClass(selection)
	return True
def compilation(): #6.4
	ret = []
	ret.append("Compile the sameple images into an exportable image recognition file")
def compileClassifier(): #6.4.1
	print("Start compiling classifier")
def changeClassifier(): #6.4.2
	print("select a different classifier to work on")
	selection = inputt.enumerateAndSelect(classifier.classifierList)
	classifier.load(selection)
	ret = ["Classifier {} loaded".format(classifier.name)]
def outputSamples(): #6.5
	ret = "Output user samples to image files for viewing and compilation\n"
	images = classifier.samples

	#Set the directory
	full_Path = "{}\\samples\\{}\\".format(Root_Path, classifier.name, time)
	try:
		os.makedirs(full_Path)
	except Exception as e:
		print(e)

	#Write the files into it
	for key,val in classifier.samples.items(): #Make the list of images without the identifying info, depend on the pic only
		#get the size
		size = val.size
		filename = full_Path + "{}-{}-{}-{}{}.png".format(size[0],size[1],key[2],key[3],key[4],key[5],classifier.name)
		val.save(filename, "PNG")
		ret += "{} saved\n".format(filename)

	return [ret]
def runObjectDetection(): #6.6
	return ["Run a camera sessions through one of the listed object detectors"]
def MobileNetDetection(): #6.6.1
	#Labels of network.
	classNames = { 0: 'background',
    1: 'aeroplane', 2: 'bicycle', 3: 'bird', 4: 'boat',
    5: 'bottle', 6: 'bus', 7: 'car', 8: 'cat', 9: 'chair',
    10: 'cow', 11: 'diningtable', 12: 'dog', 13: 'horse',
    14: 'motorbike', 15: 'person', 16: 'pottedplant',
    17: 'sheep', 18: 'sofa', 19: 'train', 20: 'tvmonitor' }

	# Next, open the video file or capture device depending what we choose, also load the model Caffe model.
	# Open video file or capture device. 
	if currentSession == None or dbFileName == None:
		return False

	#Load the Caffe model 
	net = cv2.dnn.readNetFromCaffe("MobileNetSSD_deploy.prototxt", "MobileNetSSD_deploy.caffemodel")
	files = db.getSessionFiles(currentSession) #Now we have a list of video files, lets play the video files in sequence
	totalFrames = db.getTotalFrameCount(currentSession)
	frameIndex = 0
	for f in files:
		fvs = FileVideoStream(f).start()
		#Start the video loop
		ret = fvs.more()
		frame = fvs.read() #Read in the next frame image
		frameIndex = 0
		while ret is True:
			if frame is not None:
				frame_resized = cv2.resize(frame,(300,300)) # resize frame for prediction
				blob = cv2.dnn.blobFromImage(frame_resized, 0.007843, (300, 300), (127.5, 127.5, 127.5), False)
				net.setInput(blob)
				detections = net.forward()
				#For get the class and location of object detected, 
			    # There is a fix index for class, location and confidence
    			# value in @detections array .
				for i in range(detections.shape[2]):
					confidence = detections[0, 0, i, 2] #Confidence of prediction 
				if confidence > 0.2: # Filter prediction 
					#Size of frame resize (300x300)
					cols = frame_resized.shape[1] 
					rows = frame_resized.shape[0]
					class_id = int(detections[0, 0, i, 1]) # Class label
					# Object location 
					xLeftBottom = int(detections[0, 0, i, 3] * cols) 
					yLeftBottom = int(detections[0, 0, i, 4] * rows)
					xRightTop   = int(detections[0, 0, i, 5] * cols)
					yRightTop   = int(detections[0, 0, i, 6] * rows)
			else:
				continue #No frame? try again?
			frameIndex += 1
			ret = fvs.more()
			if ret is False:
				break
			frame = fvs.read() #Read in the next frame image



"""
											STATUS
#status function reads the global variables and formats their information into context sensitive for the user to see as needed
"""
def status():
	dbStatus = Globals.get("DB") #Get the Globals and put them into locals for convenience and readability
	bbv = Globals.get("BB Video Results")
	classifier = Globals.get("Classifier")
	#Construct the text strings to put into the menu system to update context
	currentSesssionStatus = bbv.sessionRecordTime
	bbRunTime = bbv.sessionRunTime
	currentClassifier = classifier.name
	classifierFrame = classifier.frameIndex
	if bbRunTime == 0:
		bbRunTime = "not run yet"
	inputt.updateMenuItem(['2'], "Database menu({})".format(dbStatus))
	inputt.updateMenuItem(['4'], "Session({})".format(currentSesssionStatus))
	inputt.updateMenuItem(['4', '2'], "Delete Camera Session ({})".format(currentSesssionStatus))
	inputt.updateMenuItem(['5'], "BirdBuddy(run on {})".format(bbRunTime))
	inputt.updateMenuItem(['6'], "User Classification({})".format(currentClassifier))
	inputt.updateMenuItem(['6', '1'], "Select classification from {}".format(currentSesssionStatus))
	inputt.updateMenuItem(['6', '1', '1'], "Jump to Frame({})".format(classifierFrame))
	inputt.updateMenuItem(['6', '1', '<-'], "Go down one frame({})".format(classifierFrame))
	inputt.updateMenuItem(['6', '1', '->'], "Go up one frame({})".format(classifierFrame))
	inputt.updateMenuItem(['6', '4'], "Compile classifier for {}".format(currentClassifier))

"""
Root output function, good place to put welcome message, gets displayed first as the output of the root menu
"""
def root(): #A welcome screen outputted initially
	return ["Welcome to Sky Scanner.\nThis bottom part is the output screen\nThe top part is what functions you can use\nSelect one of the above options."]

#Setup the basic menu structure and the functions each option goes to
inputt.add_menu_item([], name = "Sky Scanner Root Menu Alpha", func = root)
inputt.add_menu_item(['1'] , name = "Toggle Camera", func = toggleCamera) #Tuples need 2 elements so the main menu gets a blank one
inputt.add_menu_item(['2'], name = "Database Menu", func = root2)
inputt.add_menu_item(['2', '1'], name = "Reset Database", func = resetDB)
inputt.add_menu_item(['2', '2'], name = "Switch Database", func = switchDB)
inputt.add_menu_item(['3'], name = "Status", func = root3)
inputt.add_menu_item(['3', '1'], name = "Globals", func = globalsStatus)
inputt.add_menu_item(['3', '2'], name = "Threads", func = threadsStatus)
inputt.add_menu_item(['4'], name = "Camera Session: None", func = root4)
inputt.add_menu_item(['4', '1'], name = "Select Camera Session:", func = selectCameraSession)
inputt.add_menu_item(['4', '2'], name = "Delete Camera Session", func = deleteCameraSession)
inputt.add_menu_item(['4', '2', 'y'], name = "Confirm camera session deletion", func = confirmDeleteCameraSession)
inputt.add_menu_item(['4', '3'], name = "Play back camera session", func = playBack)
inputt.add_menu_item(['4', '4'], name = "Load video file", func = Load_Video_File)
inputt.add_menu_item(['5'], name = "BBVideo: Select camera session", func = root5)
inputt.add_menu_item(['5', '1'], name = "Browse video data visualization", func = bbvDataViz)
inputt.add_menu_item(['5', '2'], name = "Run BirdBuddy", func = BBProcess)
inputt.add_menu_item(['6'], name = "User Classifications Menu", func = root6)
inputt.add_menu_item(['6', '1'], name = "Add classification sample", func = selectClassifierSample)
inputt.add_menu_item(['6', '1', '1'], name = "Jump to Frame", func = classifierJumpToFrame)
inputt.add_menu_item(['6', '1', '<-'], name = "Go down one frame", func = classifierGoDownOneFrame)
inputt.add_menu_item(['6', '1', '->'], name = "Go up one frame", func = classifierGoUpOneFrame)
inputt.add_menu_item(['6', '1', 'k'], name = "Select ROI from frame", func = selectROI)
inputt.add_menu_item(['6', '1', 'k', 'a'], name = "Accept the ROI and enter it into the database", func = acceptROI)
inputt.add_menu_item(['6', '2'], name = "Delete classification Samples", func = loadClassificationSamples)
inputt.add_menu_item(['6', '2', 'a'], name = "Select classification Sample to deleLoad_Video_Filete", func = deleteClassificationSample)
inputt.add_menu_item(['6', '3'], name = "Delete entire classification", func = deleteClassification)
inputt.add_menu_item(['6', '4'], name = "Compile classifier", func = compilation)
inputt.add_menu_item(['6', '4','1'], name = "Start compilation", func = compileClassifier)
inputt.add_menu_item(['6', '4','2'], name = "Change classifier", func = changeClassifier)
inputt.add_menu_item(['6', '5'], name = "Output User classification sample images", func = outputSamples)
inputt.add_menu_item(['6', '6'], name = "Run Object Detection", func = runObjectDetection)
inputt.add_menu_item(['6', '6','1'], name = "Run MobileNet ", func = MobileNetDetection)
inputt.add_menu_item(['6', '6','2'], name = "Run Object Detection", func = runObjectDetection)


#<- Go one frame down
#-> Go one frame up
#Left Click start selecting ROI
#   Once in left click then open another sub menu
#	Drag over ROI
#	Space/Enter Select ROI
#	C to cancel ROI
#		Submenu below select ROI
#		Enter: Confirm selection
#			Enter new name
#			
#		Escape: Cancel
#The main inputt loop, wait for the user to enter a line, process it by virtue of its current menuLevel
#[x,y,z]
#inputt.gui.resetScreens() #Initialize the display
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

#The inputt main loop update menu to show current state, process the current menu item, and get the next line of input
while True:
	db.flush_command_buffer()
	inputt.outputt()
	if inputt.endProgram:
		break
	userInput = inputt.nextLine()

#Shut down the running threads
for rt in threads.iterable():
	rt.stop()