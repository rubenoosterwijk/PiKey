# this file defines all the necessary 
from metagame import *
from backdrops import *
from pimidi import * #naam veranderd van io naar pi
import pygame
import config

class MenuClass( GameChunkClass ): # erft van de GameChunkClass
#### MENU CLASS
    def __init__( self, entries ):
        self.backdrop = LeftPianoBackDropClass()
        ## voor midi input op verschillende instellingen
        self.midiimage = pygame.image.load(os.path.join(config.RESOURCEdirectory, "respondstomidi.png"))
        self.midiimagerect = self.midiimage.get_rect()
        # setup elke entries
        self.setupentries( entries )
        # start met de eerste geselecteerde entry         
        self.currentselectedofselectable = 0 

    def setupentries( self, entries ):
        # Most belangrijke stuk van de Menuclass is een lijst van alle Entry Classes: 
        self.entries = entries
        self.numentries = len(entries)
        self.yentries = [0] # y posities van de entries
        for i in range(1,self.numentries):
            ## 
            self.yentries.append( self.yentries[-1] + self.entries[i-1].height )
        self.yentries.append( self.yentries[-1] + self.entries[-1].height ) 

## ADD HERE

        self.yoffset = 0 ## y-offset van de scherm in geval dat het scherm niet correct weergegeven is

        #kijk welke entries geselecteerd kunnen worden
        self.selectableentries = range(self.numentries)
        for i in range(self.numentries):
            if not self.entries[i].selectable:
                ## if this entry isn't selectable
                self.selectableentries.remove(i)
        
        if len( self.selectableentries ) == 0:
            Error("Initialization of MenuClass has no selectable menu items")


#### MENU CLASS
    def update( self, dt, midi ):
        self.backdrop.update( dt )

    def process( self, event, midi ):
        '''here we provide methods for changing things on the menu'''

        if event.type == pygame.KEYDOWN:
            iselected = self.selectableentries[self.currentselectedofselectable]
            if event.key == pygame.K_DOWN or event.key == pygame.K_j: #keyin.down:
                ## strike a random key on the piano.  light it up on the background:
                self.backdrop.hitrandomkey( midi, 4 ) # octave below middle C
                ## now actually move the selection
                self.currentselectedofselectable += 1
                if self.currentselectedofselectable >= len(self.selectableentries):
                    self.currentselectedofselectable = 0
                    yoffset = 0
                return {}

            elif event.key == pygame.K_UP or event.key == pygame.K_k: # keyin.up:
                ## strike a random key on the piano.  light it up on the background:
                self.backdrop.hitrandomkey( midi, 5 ) # octave of middle C
                self.currentselectedofselectable -= 1
                if self.currentselectedofselectable < 0:
                    self.currentselectedofselectable = len(self.selectableentries) - 1
                return {}

            elif event.key == K_RETURN or event.key == K_SPACE: #keyin.enter:
                ## execute the entry that is currently selected
                if self.entries[iselected].respondstomidi:
                    self.backdrop.hitkey( midi, self.entries[iselected].value )
                return self.entries[iselected].execute()

            elif event.key == pygame.K_RIGHT or event.key == pygame.K_l:
                switchvalue = self.entries[iselected].switchvalueright(pygame.key.get_mods() & pygame.KMOD_SHIFT)
                if self.entries[iselected].respondstomidi:
                    self.backdrop.hitkey( midi, self.entries[iselected].value )
                return switchvalue
                    
            elif event.key == pygame.K_LEFT or event.key == pygame.K_h:
                switchvalue = self.entries[iselected].switchvalueleft(pygame.key.get_mods() & pygame.KMOD_SHIFT)
                if self.entries[iselected].respondstomidi:
                    self.backdrop.hitkey( midi, self.entries[iselected].value )
                return switchvalue
 
            elif event.key == pygame.K_BACKSPACE:
                return self.backspaceaction

        return {}

#### MENU CLASS
    def processmidi( self, midi ):
        newnotes = midi.newnoteson()
        lastnote = -1
        for note in newnotes:
            midi.startnote( note[0], note[1], config.PIANOchannel )
            # pak de noot in octaaf (van 0 to 11) 
            octave, noteinoctave = divmod( note[0], 12 ) 
            # voor het highlighten van de key inm de achtergrond
            self.backdrop.brightenkey( note[0] ) 
            lastnote = note[0] 
            
        newnotes = midi.newnotesoff()
        for note in newnotes:
            midi.endnote( note, config.PIANOchannel ) # stop note note

        if lastnote >= 0: 
            iselected = self.selectableentries[self.currentselectedofselectable]
            if self.entries[iselected].respondstomidi:
                if lastnote in self.entries[iselected].allowedvalues:
                    self.entries[iselected].currentvalueindex = self.entries[iselected].allowedvalues.index( lastnote )
                    self.entries[iselected].setvaluefromindex()
                    return self.entries[iselected].execute()
                else:
                    Warn( "Midi note was not allowed as input to TextEntryClass" )
        return {}
        
#### MENU CLASS
    def draw(self, screen):
        '''here we draw our entries onto the screen'''
        screencenterx = screen.get_rect().centerx
        screenwidth, screenheight = screen.get_size()
        remainingheight = screenheight - self.yentries[-1]
        if remainingheight > 0:
            extrapadding = 1.0*remainingheight / (self.numentries+3)
        else:
            extrapadding = 0
            
        # voeg toe in backdrop
        self.backdrop.draw( screen )
######## zoek de entry die geselecteerd is.
        iselected = self.selectableentries[self.currentselectedofselectable]
######## loop door alle entries, geselecteerd of niet
        i=0
        while i < iselected:
            # do not highlight these entries, they are not selected
            self.entries[i].draw( screen, screencenterx, 
                                  -self.yoffset + self.yentries[i] + (i+2)*extrapadding, 0 )
            i += 1


######## als iets gehighlight is, pak zijn y positie
        yselected = -self.yoffset + self.yentries[i] + (i+2)*extrapadding
        ## so throw on a midi picture if he responds to midi
        if self.entries[i].respondstomidi:
            self.midiimagerect.y = yselected
            self.midiimagerect.left = (0.4*screenwidth + 0.6*screencenterx) 
            screen.blit( self.midiimage, self.midiimagerect )

######## highlight wat in gebruik is
        self.entries[i].draw( screen, screencenterx, yselected, 1 ) 
        i += 1

        
        while i < self.numentries:
            # deze niet highlighten want ze zijn niet geselecteerd
            self.entries[i].draw( screen, screencenterx, 
                                  -self.yoffset + self.yentries[i] + (i+2)*extrapadding, 0 )
            i += 1
        
        
            
#### END MENU CLASS



class EntryClass:
    def __init__( self, **kwargs ):
        self.allowedchanges = [ "action" ] 
        self.setstate( **kwargs )
    def setstate( self, **kwargs ):
        ## set standaard
        self.action = dict()
        ## pak user input
        for key, value in kwargs.iteritems():
            ## pak alle eigenschappen van keyword argumenten
            if key in self.allowedchanges:
                setattr( self, key, value )
            else:
                Warn("in EntryClass:setstate - key "+ key +" is protected!!")
        ## post process stuff
        ## now create the stuff that will get drawn
    def draw( self, screen, x, y, highlighted ):
        pass 
    def execute( self ):
        return self.action
            
            
        
#### END ENTRY CLASS


class TextEntryClass:
    ''' dit is voor een text entry op het menu scherm'''
#### CLASS TEXTENTRY
    def __init__( self, **kwargs ):
        self.allowedchanges = [ "text",
                                "font",
                                "infolines",
                                "fontsize",
                                "fontcolor",
                                "selectedfontcolor",
                                "respondstomidi",
                                "selectable",
                                "action",
                                "asetting",
                                "height",
                                "value",
                                "currentvalueindex",
                                "valuefontsize",
                                "captionfontcolor",
                                "allowedvalues",
                                "captionvalues",
                                "bgcolor",
                                "showleftrightarrows",
                                ] 
        self.setstate( **kwargs )

#### CLASS TEXTENTRY
    def setstate( self, **kwargs ):
        ## maak standaard aan
        self.font = config.FONT
        self.fontcolor = (255,255,255)
        self.selectedfontcolor = (255,255,255)
        self.captionfontcolor = (205,205,205)
        self.text = ""
        self.infolines = []
        self.fontsize = 24
        self.valuefontsize = 20
        self.selectable = False
        self.respondstomidi = False
        self.action = {}
        self.height = 0
        self.bgcolor = (50,50,50)
        self.asetting = False
        self.allowedvalues = []
        self.captionvalues = []
        self.showleftrightarrows = False
        self.picturefile = ""

        for key, value in kwargs.iteritems():
            if key in self.allowedchanges:
                setattr( self, key, value )
            else:
                Warn("in TextEntryClass:setstate - key "+ key +" is protected!!")

        self.fontsize *= config.FONTSIZEmultiplier
        self.valuefontsize *= config.FONTSIZEmultiplier
        self.fontsize = int(self.fontsize)
        self.valuefontsize = int(self.valuefontsize)
        
        if self.height == 0:
            if self.text:
                self.height += self.fontsize
            if self.asetting:
                self.height += self.valuefontsize
                if len(self.captionvalues) > 0:
                    self.height += 1.2*self.valuefontsize
       
        if self.asetting:
            try: 
                if self.value not in self.allowedvalues:
                    self.currentvalueindex = len(self.allowedvalues) - 1
                    self.value = self.allowedvalues[self.currentvalueindex]
                else:
                    self.currentvalueindex = self.allowedvalues.index( self.value )
            except AttributeError:
                self.currentvalueindex = len(self.allowedvalues) - 1
                self.value = self.allowedvalues[self.currentvalueindex]
            
            if self.showleftrightarrows and len(self.allowedvalues) == 1:
                self.showleftrightarrows = False

            if len(self.captionvalues) > 0:
                if len(self.captionvalues) != len(self.allowedvalues):
                    Error("Need as many captions as values, if you're going to use captions")
      
        
        ## laat alles nu runnen
        if self.text:
            fontandsize = pygame.font.SysFont(self.font, self.fontsize)
            self.label = fontandsize.render( self.text, 1, self.fontcolor )
            self.selectedlabel = fontandsize.render( self.text, 1, self.selectedfontcolor )
            self.labelbox = self.label.get_rect()

        if len(self.infolines) > 0:
            fontandsize = pygame.font.SysFont(self.font, self.fontsize - 2)
            self.infolabel = []
            self.infolabelbox = []
            for i in range(len(self.infolines)):
                self.infolabel.append( fontandsize.render( self.infolines[i], 1, self.fontcolor ) )
                self.infolabelbox.append( self.infolabel[-1].get_rect() )

        self.setvaluefromindex()

#### CLASS TEXTENTRY
    def setvaluefromindex( self ): 
        if self.asetting:
            self.value = self.allowedvalues[ self.currentvalueindex ]
            fontandsize = pygame.font.SysFont(self.font, self.valuefontsize)
            self.valuelabel = fontandsize.render( str(self.value), 1, self.fontcolor )
            self.valuelabelbox = self.valuelabel.get_rect()

            if len(self.captionvalues) > 0:
                self.captionvalue = self.captionvalues[ self.currentvalueindex ]
                self.captionlabel = fontandsize.render( self.captionvalue, 1, self.captionfontcolor )
                self.captionlabelbox = self.captionlabel.get_rect()
            self.action[self.text] = self.value
                

#### CLASS TEXTENTRY
    def draw( self, screen, x, y, highlighted ):
        screenwidth, screenheight = screen.get_size()
        if self.text:
            self.labelbox.centerx = x
            self.labelbox.centery = y
            if self.bgcolor:
                hangover = 5
                bgrect = Rect( self.labelbox.x - hangover, self.labelbox.y - 5,
                               self.labelbox.width + 2*hangover, self.labelbox.height + 10 )
                pygame.draw.rect( screen, self.bgcolor,  bgrect )
                
            if highlighted:
                screen.blit( self.selectedlabel, self.labelbox )
                # draw an underline on the text box
                pygame.draw.line( screen, self.selectedfontcolor, 
                                  self.labelbox.bottomleft, self.labelbox.bottomright )
            else:
                screen.blit( self.label, self.labelbox )

        if len(self.infolines) and highlighted:
            rightx = 0.9*screenwidth
            self.infolabelbox[0].right = rightx
            self.infolabelbox[0].top = 0.1*screenheight
            screen.blit( self.infolabel[0], self.infolabelbox[0] )
            for i in range(1,len(self.infolines)):
                self.infolabelbox[i].right = rightx
                self.infolabelbox[i].top = self.infolabelbox[i-1].bottom + 10
                screen.blit( self.infolabel[i], self.infolabelbox[i] )

        if self.asetting:
            self.valuelabelbox.centerx = x
            if self.text:
                self.valuelabelbox.top = self.labelbox.bottom + 0.5*self.fontsize
                if self.bgcolor and not self.text:
                    hangover = 5
                    bgrect = Rect( self.valuelabelbox.x - hangover, self.valuelabelbox.y - 5,
                                   self.valuelabelbox.width + 2*hangover, self.valuelabelbox.height + 10 )
            else:
                self.valuelabelbox.centery = y
                if self.bgcolor and not self.text:
                    hangover = 5
                    bgrect = Rect( self.valuelabelbox.x - hangover, self.valuelabelbox.y - 5,
                                   self.valuelabelbox.width + 2*hangover, self.valuelabelbox.height + 10 )
                pygame.draw.rect( screen, self.bgcolor,  bgrect )
                if highlighted:
                    pygame.draw.line( screen, self.selectedfontcolor, 
                                      self.valuelabelbox.bottomleft, self.valuelabelbox.bottomright )
            
            screen.blit( self.valuelabel, self.valuelabelbox )

            if len(self.captionvalues) > 0:
                self.captionlabelbox.centerx = x
                self.captionlabelbox.top = self.valuelabelbox.bottom + 0.5*self.fontsize
                screen.blit( self.captionlabel, self.captionlabelbox )


            if highlighted and self.showleftrightarrows:
                # highlight de knoppen in gebruik left|right
                if self.text:
                    rightx = self.labelbox.right + 20
                    leftx = self.labelbox.left - 20
                    topy = y + self.fontsize
                else:
                    rightx = self.valuelabelbox.right + 20
                    leftx = self.valuelabelbox.left - 20
                    topy = self.valuelabelbox.top

                boty = topy + 20
                midy = topy + 10
                triwidth = 15
                # teken een driehoek
                pygame.draw.polygon(screen, self.selectedfontcolor,
                                            [ ( rightx, topy ), 
                                              ( rightx + triwidth, midy ), 
                                              ( rightx, boty ) ] )
                # draw left triangle
                pygame.draw.polygon(screen, self.selectedfontcolor,
                                            [ ( leftx, boty ), 
                                              ( leftx  - triwidth, midy ), 
                                              ( leftx, topy ) ] )
                  
#### CLASS TEXTENTRY
    def execute( self ):
        return self.action
    
#### CLASS TEXTENTRY
    def switchvalueright( self, bigshift = False ):
        if self.asetting and len(self.allowedvalues) > 0:
            if bigshift: 
                self.currentvalueindex += max(1, len(self.allowedvalues)/10)
            else:
                self.currentvalueindex += 1

            if self.currentvalueindex >= len(self.allowedvalues):
                self.currentvalueindex = 0
            
            self.setvaluefromindex()

            if self.text:
                return { self.text : self.value }
        return {}
            
#### CLASS TEXTENTRY
    def switchvalueleft( self, bigshift = False ):
        if self.asetting and len(self.allowedvalues) > 0:
            if bigshift: 
                self.currentvalueindex -= max(1, len(self.allowedvalues)/10)
            else:
                self.currentvalueindex -= 1

            if self.currentvalueindex < 0:
                self.currentvalueindex = len(self.allowedvalues) - 1
            
            self.setvaluefromindex()
            if self.text:
                return { self.text : self.value }
        return {}

#### END TEXTENTRY CLASS

class DirectoryMenuClass( MenuClass ): # erft van de DisplayClass
#### DIRECTORY MENU CLASS
    def __init__( self, extraentries, rootdir, creatoraction={} ):
        self.backdrop = LeftPianoBackDropClass()
        self.rootdir = str(rootdir)
        self.extraentries = extraentries 
        self.font = config.FONT
        self.fontcolor = (255,255,255)
        self.fontsize = 18

        # voor het pakken van informatie...
        self.listeningfortext = False
        self.askingfor = ""
        self.listeningmessage = ""
        self.listeningaction = creatoraction
        
        if len(creatoraction) == 0:
            self.creator = False
        else:
            self.creator = True
            self.extraentries.append( TextEntryClass( text="Mode", fontsize=18,
                                                      fontcolor=self.fontcolor,
                                                      selectable=True,
                                                      bgcolor=randomcolor(),
                                                      valuefontsize=self.fontsize,
                                                infolines=["Druk op [enter] om iets te maken,",
                                                           "selecteer edit/new met left/right arrows",
                                                           "of [backspace] naar main menu"],
                                                  allowedvalues=["Edit", "New"],
                                                  value="Edit",
                                                  asetting=True,
                                                  showleftrightarrows=True,
                                                  action=creatoraction ) )
                                                  #selectedfontcolor=randomcolor() ) )


        self.mode = 0   

        self.allowedsubdirs = [ os.walk(self.rootdir).next()[1] ] # 1 pakt directories en 0 laat je door ze heen scrollen
        if len(self.allowedsubdirs[0]) == 0:
            Error(" No directories found in directory "+self.rootdir+". ")
        
        if self.creator:
            # als we in create mode zijn, laat zien welke compositions je hebt
            self.currentsubdir = [ "Compositions" ]
        else:
            #pak een random directory in rootdir:
            self.currentsubdir = [ self.allowedsubdirs[0][int(random()*len(self.allowedsubdirs[0]))] ]

        self.directoryentries = [ TextEntryClass( fontsize=18,
                                                  fontcolor=self.fontcolor,
                                                    bgcolor=randomcolor(),
                                                  selectable=True,
                                                  valuefontsize=self.fontsize,
                                                infolines=["Choose a top directory with left/right arrows."],
                                                  height=-25,
                                                  allowedvalues=self.allowedsubdirs[0],
                                                  asetting=True,
                                                  value=self.currentsubdir[0],
                                                  showleftrightarrows=True ) ]
                                                  #selectedfontcolor=randomcolor() ) ]

        # descend in de directory
        self.descend()            
        self.currentselectedofselectable = 0 # welke menu entry is geselecteerd

    def descend( self, startingdepth = 1, maxdepth = 6 ): 
        ''' here we plot a random descent into the directory structure '''
        descendingdirectory = self.rootdir
        for i in range(startingdepth):
            descendingdirectory = os.path.join( descendingdirectory, self.currentsubdir[i] )

        del self.allowedsubdirs[startingdepth:] # delete alles na de starting depth
        del self.directoryentries[startingdepth:] # alles wordt gerecreerd
        del self.currentsubdir[startingdepth:] # we maken een nieuwe lijst aan van current directories

        descendingdirectorycontents = os.walk(descendingdirectory).next()[1] # 1 alleen voor directories
        numcontents = len(descendingdirectorycontents)
        currentdepth = startingdepth
        while numcontents > 0 and currentdepth <= maxdepth:
            ## voeg de inhoud van de ene directory in de ander
            self.allowedsubdirs.append( descendingdirectorycontents )
            # kies een random entry dat geselecteerd wordt
            self.currentsubdir.append( self.allowedsubdirs[-1][int(  random()*numcontents  )] )

            descendingdirectory = os.path.join(descendingdirectory,self.currentsubdir[-1])
            # kijk naar de inhoud van de directory
            descendingdirectorycontents = os.walk(descendingdirectory).next()[1] # 1 is alleen voor directories
            # kijkt hoeveel er zijn
            numcontents = len(descendingdirectorycontents)

            # maak een text entry voor hem
            if numcontents:
                self.directoryentries.append( TextEntryClass( selectable=True,
                                                          height = -25, # dit gooit alles stukken bij elkaar, hoe langer hoe dichter op elkaar
                                                          valuefontsize=self.fontsize,
                                                          fontcolor=self.fontcolor,
                                              infolines=["Choose sub-directory with left/right arrows."],
                                                          allowedvalues=self.allowedsubdirs[-1],
                                                          fontsize=18,asetting=True,
                                                          value=self.currentsubdir[-1], 
                                                          showleftrightarrows=True,
                                                          bgcolor=randomcolor() ) )
            elif self.mode == 0: 
                self.directoryentries.append( TextEntryClass( selectable=True,
                                                          height = -25,
                                                          valuefontsize=self.fontsize,
                                                          fontcolor=self.fontcolor,
                                              infolines=["Choose piece with left/right arrows."],
                                                          allowedvalues=self.allowedsubdirs[-1],
                                                          fontsize=18,asetting=True,
                                                          value=self.currentsubdir[-1], 
                                                          showleftrightarrows=True,
                                                          bgcolor=randomcolor()) )
                                                          

            currentdepth += 1
        
        if (currentdepth >= maxdepth and numcontents > 0):
            Error(" Your file directory is too deep.  Simmer down! ")
       
        
        # voeg wat actie toe. "descendingdirectory" is eigenlijk de directory ten opzichte van root.
        # dus we willen de "piecedir" voor het hoofdspel kunnen veranderen door op enter te drukken
        # vrijwel alle inzendingen.
        # maak ze klaar voor weergave
        if self.creator:
            self.extraentries[-1].action["piecedir"] = descendingdirectory
            for d in self.directoryentries:
                d.action =  { "piecedir" : descendingdirectory,
                              "gamestate" : self.extraentries[-1].action["gamestate"],
                              "printme" : self.extraentries[-1].action["printme"]  }
        else:
            self.extraentries[1].action["piecedir"] = descendingdirectory
            for d in self.directoryentries:
                d.action =  { "piecedir" : descendingdirectory,
                              "gamestate" : self.extraentries[1].action["gamestate"],
                              "printme" : self.extraentries[1].action["printme"]  }

        self.setupentries( self.extraentries + self.directoryentries )

#### DIRECTORY MENU CLASS
    def update( self, dt, midi ):
        self.backdrop.update( dt )

    def process( self, event, midi ):
        '''here we provide methods for changing things on the menu'''
        if event.type == pygame.KEYDOWN:
            if self.listeningfortext: 
                if event.key == pygame.K_BACKSPACE:
                    self.listeningmessage = self.listeningmessage[0:-1] # verwijder laatst ingevoerd tekst
                elif event.key == pygame.K_RETURN:
                    self.listeningfortext = False
                    self.listeningaction[self.askingfor] = self.listeningmessage # add entry
                    print "Listened, and got ", self.listeningmessage
                    return self.listeningaction
                elif event.key < 128:
                    newletter = chr(event.key) #dit is de nieuwe letter
                    if pygame.key.get_mods() & pygame.KMOD_SHIFT: # als de shift key ingedrukt is
                        newletter = newletter.upper() #maakt de letter een hoofdletter
                    self.listeningmessage += newletter 
                    

            else: 
                # als we aan het wachten zijn voor normale input
                iselected = self.selectableentries[self.currentselectedofselectable]
                if event.key == pygame.K_DOWN or event.key == pygame.K_j: #keyin.down:
                    ## random key voor highlight key op de achtergrond
                    self.backdrop.hitrandomkey( midi, 4 ) # octaaf onder middle C
                    self.currentselectedofselectable += 1
                    if self.currentselectedofselectable >= len(self.selectableentries):
                        self.currentselectedofselectable = 0
                        yoffset = 0
                    return {}

                elif event.key == pygame.K_UP or event.key == pygame.K_k: # keyin.up:
                    ## random key voor highlight key op de achtergrond
                    self.backdrop.hitrandomkey( midi, 5 ) # octaaf middle C
                    self.currentselectedofselectable -= 1
                    if self.currentselectedofselectable < 0:
                        self.currentselectedofselectable = len(self.selectableentries) - 1
                    return {}

                elif event.key == K_RETURN or event.key == K_SPACE: #keyin.enter:
                    ## execute entry dat is geselecteerd
                    if self.entries[iselected].respondstomidi:
                        self.backdrop.hitkey( midi, self.entries[iselected].value )

                    if iselected == len(self.extraentries) - 1:
                        # dit is de edit command mode
                        if self.extraentries[iselected].value == "New":
                            self.listeningfortext = True
                            self.askingfor = "Name"
                            return {}
                            
                    return self.entries[iselected].execute()

                elif event.key == pygame.K_RIGHT or event.key == pygame.K_l:
                    try:
                        oldvalue = self.entries[iselected].value
                        switchaction = self.entries[iselected].switchvalueright(pygame.key.get_mods() & pygame.KMOD_SHIFT)
                        newvalue = self.entries[iselected].value
                        if self.entries[iselected].respondstomidi:
                            self.backdrop.hitkey( midi, self.entries[iselected].value )

                        if oldvalue != newvalue:
                            depth =  iselected - len(self.extraentries) + 1
                            if depth == 0 and self.creator: ## we hebben new/create aangewezen in de menu
                                if self.extraentries[iselected].value == "Edit":
                                    # je bent nu in edit
                                    self.mode = 0
                                else:
                                    # je bent nu in create
                                    self.mode = 1
                                depth = max(1, len(self.currentsubdir) - 1)
                                self.descend( depth )
                                return {}
                            elif depth > 0:
                                self.currentsubdir[depth-1] = self.entries[iselected].value
                                self.descend( depth )
                                return {}
                        return switchaction
                    except AttributeError:
                        return {}
                        
                elif event.key == pygame.K_LEFT or event.key == pygame.K_h:
                    try:
                        oldvalue = self.entries[iselected].value
                        switchaction = self.entries[iselected].switchvalueleft(pygame.key.get_mods() & pygame.KMOD_SHIFT)
                        newvalue = self.entries[iselected].value
                        if self.entries[iselected].respondstomidi:
                            self.backdrop.hitkey( midi, self.entries[iselected].value )

                        if oldvalue != newvalue:
                            # dit is nieuw in de directory class
                            depth =  iselected - len(self.extraentries) + 1
                            if depth == 0 and self.creator: ## we hebben new/create aangewezen in de menu
                                if self.extraentries[iselected].value == "Edit":
                                    # we zijn nu in edit
                                    self.mode = 0
                                else:
                                    # je ebnt nu in create
                                    self.mode = 1
                                depth = max(1, len(self.currentsubdir) - 1)
                                self.descend( depth )
                                return {}
                            elif depth > 0:
                                self.currentsubdir[depth-1] = self.entries[iselected].value
                                self.descend( depth )
                                return {}
                        return switchaction
                    except AttributeError:
                        return {}

                elif event.key == pygame.K_BACKSPACE:
                    return self.backspaceaction
 
        return {}

#### DIRECTORY MENU CLASS
    def draw( self, screen ):
        MenuClass.draw( self, screen )
        screenwidth, screenheight = screen.get_size()

        if self.listeningfortext:
            fontandsize = pygame.font.SysFont(self.font, self.fontsize)
            listenerlabel = fontandsize.render( self.askingfor + ": " + self.listeningmessage, 
                                                1, self.fontcolor )
            listenerbox = listenerlabel.get_rect()
            listenerbox.left = 0.2*screenwidth
            listenerbox.bottom = screenheight - 10
            screen.blit( listenerlabel, listenerbox )


#### END DIRECTORY MENU CLASS




