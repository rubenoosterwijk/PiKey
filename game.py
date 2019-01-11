# metagame includes basic stuff on backdrops and the gamechunk class
from metagame import *
# playclass erft van de gamechunk class:  het spel
from play import *
# menuclass erft van de gamechunk voor de main menu, instellingen menu, etc.
from menu import *
# voor midi input van keyboard en midi output van fluidsynth
from pimidi import *
# voor het editten van composities
from edit import *
# voor het lezen en schrijven van dictionaries
import pickle
# configuratie file voor random computer/OS-specific guys
import config
    
class GameClass:
#### GAMECLASS
    def __init__( self ):
        # maakt gebruik van de pygame module
        pygame.init()
        pygame.mouse.set_visible( False ) # geen mouse pointer(alleen werken met arrow keys
        pygame.fastevent.init() ## we hebben fastevents nodig voor midi input
        self.midi = MidiClass()

        ## GAME STATE AND OTHER GLOBAL SETTINGS
        ## the following may be changed in "setstate"
        self.allowedchanges = [ "gamestate",    # een integer, zie config.py
                                "settings",     # voor fullscreen, etc.
                                "piecedir",     # directory voor edit en compose functies
                                "printme" ]

        self.printme = ""  

        ## GLOBAL SPEL INSTELLINGEN
        self.allowedsettings = [ "Midi Input Channel",    
                                 "Lowest Note", 
                                 "Highest Note", 
                                 "Fullscreen" ]
        
        ## probeer spel instellingen te laden als dat niet werkt, gebruik standaard instellingen
        try:
            settingsdir = os.path.join( config.RESOURCEdirectory, "settings.pkl" )
            with open(settingsdir, 'rb') as handle:
                self.settings = pickle.loads( handle.read() )
        except IOError:
            print "settings file does not exist.  setting defaults."
            self.settings = { 'Midi Input Channel': 3,  # het is 3 voor onze apparaat.
                              'Lowest Note': 9,        # laagste noot
                              'Highest Note': 96,      # hoogste noot
                              'Fullscreen': 0 }        
       
        ## dit geeft een lijst met beschikbare midi inputs
        ##  of als er helemaal geen midi input is
        self.checkandsetmidi()

        ## INDIVIDUELE SPEL INSTELLINGEN
        self.allowedpiecesettings = [ "Name",
                                      "TempoPercent",   # percentage van de tempo
                                      "Difficulty",  # integer 
                                      "PlayerTrack",
                                      "Metronome",
                                      "BookmarkTicks",
                                      "Sandbox" ]    # Als true, dan krijg je geen min-punten

        ## LOPENDE MAKEN VAN DE GAMESTATE
        ## maak de gamestate.  eerst is het niks dus (-1) zodat het met niets in conflict komt
        self.gamestate = -1
        # anders gaat het niet naar de goede state als je het volgende doet:
        self.setstate( gamestate=config.GAMESTATEmainmenu )

        ## maak de klok aan
        self.clock = pygame.time.Clock()

        # load and set the logo
        logo = pygame.image.load(os.path.join(config.RESOURCEdirectory, "logo32x32.png")) #awesome piano logo
        pygame.display.set_icon(logo)
        pygame.display.set_caption("PiKey") 

        self.displayinfo = pygame.display.Info()

        self.setscreen()

#### GAMECLASS
    def checkandsetmidi( self ): 
        '''dit geeft ons een lijst van alle beschikbare midi inputs, en resets de midi input channel
        in de instellingen als de ene die je nu hebt geen channel heeft'''
        self.midiinputs, self.midiinputnames = self.midi.getallowedinputs()
        if len(self.midiinputs) == 0:
            Warn("Geen herkenbare midi inputs.  sluit een midi device aan.")
        else:
            if self.settings["Midi Input Channel"] not in self.midiinputs:
                self.settings["Midi Input Channel"] = self.midiinputs[-1] 

        self.midi.setinput( self.settings["Midi Input Channel"] )

    def setscreen( self, newsize=config.DEFAULTresolution ):
        if self.settings['Fullscreen']: 
            self.screen = pygame.display.set_mode( (self.displayinfo.current_w, self.displayinfo.current_h),
                                                   pygame.FULLSCREEN ) 
        else: 
            self.screen = pygame.display.set_mode( newsize, pygame.RESIZABLE ) #display resolution
        

#### GAMECLASS
    def setstate( self, **kwargs ):
######## GAMECLASS:setstate
        oldgamestate = self.gamestate
        for key, value in kwargs.iteritems():
            allowed = False # deze key mag je niet gebruiken
            ## pak alle nieuwe eigenschappen van de keyword arguments
            if key in self.allowedchanges:
                setattr( self, key, value )
                allowed = True
            else:
                if key in self.allowedsettings:
                    originalvalue = self.settings[key]
                    self.settings[key] = value
                    allowed = True
                    if key == "Midi Input Channel": # als de gebruiker de midi input veranderd heeft,
                        self.checkandsetmidi()      # probeer het dan te resetten
                    elif key == "Fullscreen" and originalvalue != value: # we gaan de instellingen veranderen
                        self.setscreen()
                elif key in self.allowedpiecesettings:
                    self.piecesettings[key] = value
                    allowed = True
            if not allowed:            
                Warn("in GameClass:setstate - key "+ key +" is protected!!")

######## GAMECLASS:setstate
        if self.gamestate != oldgamestate:
            print "Changing gamestate from",oldgamestate,"to ",self.gamestate
            if self.printme:
                print self.printme
            print
            self.printme = ""

            if oldgamestate == config.GAMESTATEsettings: # als we in de instellingen zijn
                print "saving settings:"
                print self.settings
                try:
                    settingsdir = os.path.join( config.RESOURCEdirectory, "settings.pkl" )
                    with open(settingsdir, 'wb') as handle:
                        pickle.dump(self.settings, handle)
                except IOError:
                    print "WAARSCHUWING.  error met het opslaan van de instellingen."

############ GAMECLASS:setstate:  proberen van een nieuwe gamestate, laad menus of play mode

            if self.gamestate == config.GAMESTATEplay: #standaard play
                self.gamechunk = PlayClass( self.piecedir, self.midi, self.piecesettings )
            
############ GAMECLASS:setstate:  proberen van een nieuwe gamestate, laad menus of play mode

            elif self.gamestate == config.GAMESTATEmainmenu: #main menu
                self.gamechunk = MenuClass( [ TextEntryClass( text="Main Menu",
                                                              selectable=False,
                                                              fontsize=25 ),
                                              TextEntryClass( text="Play",
                                                              bgcolor=(50,0,10),
                                                              infolines=["Klik [enter] om te spelen,",
                                                                         "of gebruik de pijltjes toetsen om te bewegen"],
                                                              selectable=True,
                                                              fontsize=20,
                                                              action={'gamestate':config.GAMESTATEpieceselection, # level selectie
                                                                      'printme':"Selecteer je level."} ),
                                              TextEntryClass( text="Create",
                                                              bgcolor=(80,80,0),
                                                              infolines=["Klik [enter] om iets te maken,",
                                                                         "of gebruik de pijltjes toetsen om te bewegen"],
                                                              selectable=True,
                                                              #selectedfontcolor=randomcolor(),
                                                              fontsize=20,
                                                              action={'gamestate':config.GAMESTATEeditmenu, 
                                                                      'printme':"We gaan nu naar de edit menu."} ),
                                              TextEntryClass( text="Settings",
                                                              bgcolor=(10,60,0),
                                                              infolines=["Klik [enter] om je instellingen te kiezen,",
                                                                         "of gebruik de pijltjes toetsen om te bewegen"],
                                                              selectable=True,
                                                              #selectedfontcolor=(0,200,140),
                                                              fontsize=20,
                                                              action={'gamestate':config.GAMESTATEsettings, # setting selection
                                                                      'printme':"maak je instellingen aan."} ),
                                              TextEntryClass( text="Exit",
                                                              bgcolor=(0,30,50),
                                                              selectable=True,
                                                              infolines=["Press [enter] to quit,",
                                                                         "of gebruik de pijltjes toetsen om te bewegen"],
                                                              fontsize=20,
                                                              #selectedfontcolor=(255,100,0),
                                                              action={'gamestate':0, # quitting
                                                                      'printme':"leave de main menu."} )
                                                 ] ) 
                self.gamechunk.setbackspaceaction( {'gamestate':0,
                                             'printme':"exiting main menu via backspace."} )
                
                image = pygame.image.load(os.path.join(config.RESOURCEdirectory,"Pikey.png"))
                self.gamechunk.backdrop.addimage( image, "center" )

############ GAMECLASS:setstate:  proberen van een nieuwe gamestate, laad menus of play mode

            elif self.gamestate == config.GAMESTATEpieceselection: # open piece menu
                
                self.gamechunk = DirectoryMenuClass( [ TextEntryClass( text="Piece Menu",
                                                              selectable=False,
                                                              fontsize=25 ), 
                  TextEntryClass( text="Play",
                                  selectable=True,
                                  infolines=["Klik [enter] om een piece te kiezen,",
                                             "of gebruik de pijltjes toetsen om te bewegen"],
                                  fontsize=18,
                                  #selectedfontcolor=(0,200,150),
                                  bgcolor=(0,100,50),
                                  #selectedfontcolor=(0,200,150),
                                  action={'gamestate':config.GAMESTATEpiecesettings,
                                  "printme" : "piece gekozen."} ),
                  TextEntryClass( text="terug naar Main Menu",
                                  selectable=True,
                                  fontsize=18,
                                  infolines=["Klik [enter] om terug te gaan,",
                                             "of gebruik de pijltjes toetsen om te bewegen"],
                                  height=25,
                                  bgcolor=(100,10,10),
                                  #selectedfontcolor=(255,50,50),
                                  action={'gamestate':config.GAMESTATEmainmenu,
                                     'printme':"terug naar main menu."} ),
                  TextEntryClass( text="Selection",
                                  fontsize=22,
                                  height=-20, #negative hoogte maakt het wat dicht op elkaar
                                  selectable=False,
                                  valuefontsize=20 ) ],
                config.PIECEdirectory) # rootdir voor onze directory
                
                self.gamechunk.setbackspaceaction( {'gamestate':config.GAMESTATEmainmenu,
                                             'printme':"terug naar main menu via backspace."} )

            elif self.gamestate == config.GAMESTATEeditmenu: #  compose menu
                self.piecesettings = {}
                self.gamechunk = DirectoryMenuClass( [ TextEntryClass( text="Compose Menu",
                                                              selectable=False,
                                                              fontsize=25 ) ], 
                                            config.PIECEdirectory,  
                 {'gamestate':config.GAMESTATEedit, 
                 'printme':"Ga naar edit mode."}  ) 
                
                # zonder de volgende code kan je niet terug naar de main menu
                self.gamechunk.setbackspaceaction( {'gamestate':config.GAMESTATEmainmenu,
                                             'printme':"ga terug naar main menu via backspace."} )
            
            elif self.gamestate == config.GAMESTATEedit: #editing!
                if "Name" in self.piecesettings.keys():
                    piecedir = self.piecedir.split( os.path.sep )
                    piecedir = piecedir[:3] 
                    self.piecedir = (os.path.sep).join( piecedir ) 
                    self.piecedir = os.path.join( self.piecedir, self.piecesettings["Name"] )
                    if os.path.isdir(self.piecedir):
                        pass
                    else:
                        print "Creating new music directory",self.piecedir, "for editting"
                        os.makedirs( self.piecedir )
                else:
                    print "Opening",self.piecedir, "for editting"

                self.piecesettings = getpiecesettings( self.piecedir )
                self.gamechunk = EditClass( self.piecedir, self.midi, self.piecesettings )

            elif self.gamestate == config.GAMESTATEpiecesettings: #  piece settings menu
                self.piecesettings = getpiecesettings( self.piecedir )
                self.piecesettings["Metronome"] = config.METRONOMEdefault
                print "piece settings = ", self.piecesettings
                
                piecemenu = [ TextEntryClass( text="Piece Settings",
                                              selectable=False,
                                              fontsize=25 ),
                              TextEntryClass( text="Play",
                                              selectable=True,
                                              fontsize=18,
                                              infolines=["Klik [enter] om te spelen!",
                                                         "of gebruik de pijltjes toetsen om te bewegen"],
                                              bgcolor=(100,10,10),
                                              #selectedfontcolor=(255,50,50),
                                              action={'gamestate':config.GAMESTATEplay,
                                                        'printme':"start game!"} ),  
                              TextEntryClass( text="Sandbox",
                                              asetting=True, # a flag for fancy setting behavior
                                              selectable=True,
                                              fontsize=18,
                                              valuefontsize=15,
                                              allowedvalues = [0,1],
                                              value=self.piecesettings["Sandbox"],
                                                              infolines=["Choose 1",
                                                                         "to avoid grading"],
                                              #selectedfontcolor=(255,50,50),
                                              bgcolor=(100,100,0),
                                              showleftrightarrows=True),
                              TextEntryClass( text="TempoPercent",
                                              asetting=True, # a flag for fancy setting behavior
                                              selectable=True,
                                              fontsize=18,
                                              valuefontsize=15,
                                              allowedvalues=range(20,201),
                                              value=100,
                                                      infolines=["procent met wat",
                                                                 "je de tempo kan veranderen."],
                                              bgcolor=(50,100,0),
                                              #selectedfontcolor=(255,50,50),
                                              showleftrightarrows=True),
                              TextEntryClass( text="Difficulty",
                                              asetting=True, # a flag for fancy setting behavior
                                              selectable=True,
                                              fontsize=18,
                                              valuefontsize=15,
                                                      infolines=["Stel de moeilijksheidgraad in."],
                                              allowedvalues = self.piecesettings["AllowedDifficulties"],
                                              value=self.piecesettings["Difficulty"],
                                              bgcolor=(0,100,50),
                                              #selectedfontcolor=(255,50,50),
                                              showleftrightarrows=True) ]
                try:
                    if len(self.piecesettings["AllowedPlayerTracks"]) > 1:
                        piecemenu.append( TextEntryClass( text="PlayerTrack",
                                                  asetting=True, # a flag for fancy setting behavior
                                                  selectable=True,
                                                  fontsize=18,
                                                  valuefontsize=15,
                                                  allowedvalues = self.piecesettings["AllowedPlayerTracks"],
                                                  infolines=["Kies welke track","de gebruiker speelt"],
                                                  value=self.piecesettings["PlayerTrack"],
                                                  #selectedfontcolor=(255,50,50),
                                                  bgcolor=(0,50,100),
                                                  showleftrightarrows=True) )
                except KeyError:
                    self.piecesettings["PlayerTrack"] = config.DEFAULTplayertrack
                    
                piecemenu.append( TextEntryClass( text="Metronome",
                                          asetting=True, # a flag for fancy setting behavior
                                          selectable=True,
                                          fontsize=18,
                                          valuefontsize=15,
                                          allowedvalues = [ True, False ],
                                          infolines=["metronome on/off"],
                                          value=self.piecesettings["Metronome"],
                                          #selectedfontcolor=(255,50,50),
                                          bgcolor=(100,100,100),
                                          showleftrightarrows=True) )

                piecemenu.append( TextEntryClass( text="Terug naar Main Menu",
                                                  selectable=True,
                                                  fontsize=18,
                                                  #selectedfontcolor=(255,50,50),
                                                  bgcolor=(100,0,100),
                                                  action={'gamestate':config.GAMESTATEpieceselection,
                                                            'printme':"terug naar piece selection."} ) )
                self.gamechunk = MenuClass( piecemenu )
                
                self.gamechunk.setbackspaceaction( {'gamestate':config.GAMESTATEpieceselection,
                                             'printme':"terug naar main menu via backspace."} )

            elif self.gamestate == config.GAMESTATEsettings: # open settings menu
                self.checkandsetmidi()

                self.gamechunk = MenuClass( [ TextEntryClass( text="Settings Menu",
                                                              selectable=False,
                                                              fontsize=25 ), 
                                        TextEntryClass( text="Midi Input Channel",
                                                        selectable=True,
                                                        fontsize=18,
                                                        valuefontsize=15,
                                      infolines=["Wissel tussen de midi channels", "m.b.v de links/rechts pijltjes,",
                                                 "probeer daarna te spelen ", "met je midi keyboard.",
                                                 "Als je vergeten was", "je keyboad aan te sluiten,", "restart",
                                                "het spel."],
                                                        asetting=True, 
                                                        value=self.settings["Midi Input Channel"],
                                                        allowedvalues=self.midiinputs,
                                                        captionvalues=self.midiinputnames,
                                                        showleftrightarrows=True,
                                                        bgcolor=(100,10,120) ),
                                        TextEntryClass( text="Laagste noot",
                                                        selectable=True,
                                                        fontsize=18,
                                                        valuefontsize=15,
                                      infolines=["Wanneer midi input is vastgesteld,",
                                                 "speel de laagste noot", "op de keyboard,",
                                                 "of stel het in", "met de links/rechts pijltjes"],
                                                        asetting=True,
                                                        value=self.settings["Laagste noot"],
                                                        respondstomidi=True, 
                                                        allowedvalues=range(21,97),
                                                        showleftrightarrows=True,
                                                        bgcolor=(10,100,30) ),
                                        TextEntryClass( text="Hoogste noot",
                                                        selectable=True,
                                                        fontsize=18,
                                                        valuefontsize=15,
                                      infolines=["Wanneer midi input is vastgesteld,",
                                                 "speel de hoogste noot", "op de keyboard,",
                                                 "of stel het in", "met de links/rechts pijltjes"],
                                                        asetting=True, 
                                                        value=self.settings["Hoogste noot"],
                                                        respondstomidi=True,
                                                        allowedvalues=range(33,109),
                                                        showleftrightarrows=True,
                                                        bgcolor=(150,150,0) ),
                                        TextEntryClass( text="Fullscreen",
                                                        selectable=True,
                                                        fontsize=18,
                                      infolines=["Wissel full-screen","met links/rechts pijltjes."],
                                                        valuefontsize=15,
                                                        asetting=True, 
                                                        value=self.settings["Fullscreen"],
                                                        allowedvalues=[0,1],
                                                        captionvalues=["off","on"],
                                                        showleftrightarrows=True,
                                                        bgcolor=(100,50,00) ),
                                        TextEntryClass( text="Terug to Main Menu",
                                                        selectable=True,
                                                        fontsize=18,
                                      infolines=["Klik [enter] om terug te gaan",
                                                 "naar de main menu"],
                                                        bgcolor=(50,25,25) ,
                                                        action={'gamestate':config.GAMESTATEmainmenu,  
                                                                'printme':"Terug naar main menu."} ) ] )
############ GAMECLASS:setstate:
                self.gamechunk.setbackspaceaction( {'gamestate':config.GAMESTATEmainmenu,
                                             'printme':"terug naar main menu met backspace toets"} )

            elif self.gamestate == 0:
                self.quit()

        else:

            pass

######## end GAMECLASS:setstate

#### GAMECLASS
    def mainloop( self ): 
        while self.gamestate:     
            dt = self.clock.tick()

            self.midi.update( dt )

            self.gamechunk.update( dt, self.midi )
            

            self.gamechunk.draw( self.screen )
            
            processmidi = False # 
            for event in pygame.fastevent.get(): # fastevents nodig voor de midi
                if event.type == QUIT:
                    self.gamestate = 0
                elif event.type == VIDEORESIZE:
                    if event.size[0] > 100 and event.size[1] > 100:
                        self.setscreen( event.size )
                    else:
                        print "te klein"
                        self.quit()
                elif self.midi.process( event ):
                    processmidi = True 
                else:
                    ## sta de event toe om veranderingen te maken aan de midi
                    returnvalue = self.gamechunk.process( event, self.midi )
                # zorgt voor een dictionary 
                    if ( len(returnvalue) > 0 ):
                        self.setstate( **returnvalue )
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_F11:
                            self.setstate( Fullscreen = (not self.settings["Fullscreen"]) )
                
            if processmidi:  
                returnvalue = self.gamechunk.processmidi( self.midi )
                if ( len(returnvalue) > 0 ):
                    self.setstate( **returnvalue )

            ##"This will update the contents of the entire display. " (pygame documentatie)
            pygame.display.flip()
        
        self.quit()
    
    def quit( self ):
        # fullscreen uitzetten voor zekerheid als pygame midi vast loopt (gebeurt soms)
        self.settings['Fullscreen'] = False
        self.setscreen()

        self.midi.quit()
        pygame.quit()
        sys.exit()

#### end GAMECLASS
            
