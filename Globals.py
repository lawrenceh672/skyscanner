from parameters import Parameters

#set the global variables
Globals = Parameters({})

inputt = None
Globals.set("inputt",inputt) #The interface 
Globals.setDescription("inputt", "The interface")

classifier = None #A Classifier object to hold samglobalsles and generate classifiers, and to run the classifier on other sessions
Globals.set("Classifier", classifier) #The classification samglobalsle extractor and analyzer
Globals.setDescription("Classifier", "The classification sample extractor and analyzer")

dbFileName = None
db = None #Create the container class for the birdbuddy database
Globals.set("DB", db) #"The database connection"
Globals.setDescription("DB", "The database connection")

currentSession = None #A global variable to see what session were working on, the path to its saved files the key to the database
Globals.set("Camera Session", currentSession) #The camera session file path
Globals.setDescription("Camera Session", "The camera session file path")

bb = None #A BirdBuddy Object to handle motion tracking
Globals.set("BirdBuddy", bb) #"The movement tracking algorithm, saved to the database"
Globals.setDescription("BirdBuddy", "The movement tracking algorithm, saved to the database")

bbv = None  #Hold the tracking information from a BB processed video in memory
Globals.set("BB Video Results", bbv) #BirdBuddy results database to python object for analysis
Globals.setDescription("BB Video Results", "BirdBuddy results database to python object for analysis")

threads = Parameters({}) #Used to convey thread information to all threads and to set locks on global variables transparentally

threads.set("GUI", None)
threads.setDescription("GUI", "The thread that displays and updates the command line gui window")
