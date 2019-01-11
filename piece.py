# piece.py heeft class die gebruikt worden om midi files te importeren, 
# exporten en omzetten naar leesbare versies voor de pikey
# ook 'methods' om de makkelijk aan te passen. 
from metagame import *
import midi as MIDI # van python-midi om makkelijk midi' 
from midi import *
import config
import pickle, os
import operator # goeie volgorde midi events

def getpiecesettings( piecedir ):
    settings = {} #
    try:
        piecesettingsfile = os.path.join( piecedir, "info.pkl" )
        with open(piecesettingsfile, 'rb') as handle:
            settings = pickle.loads( handle.read() )
    except IOError:
        Warn(" geen info.kpl ")
    
    # moeilijkheidsgraden bepalen/ vaststellen
    descendingdirectorycontents = os.walk(piecedir).next()[2] # 2 = alleen bestanden, geen folders
    difficulties = []
    for f in descendingdirectorycontents:
        if f[-4:] == ".mid":
            difficulties.append( int(f[-5]) )

    if len(difficulties):
        difficulties.sort()
        settings["AllowedDifficulties"] = difficulties
        settings["Difficulty"] = difficulties[0]
    else:
        settings["AllowedDifficulties"] = [ config.DEFAULTdifficulty ]
        settings["Difficulty"] = config.DEFAULTdifficulty
        
    
    if not "BookmarkTicks" in settings:
        settings["BookmarkTicks"] = [] 
    if not "Metronome" in settings:
        settings["Metronome"] = config.METRONOMEdefault

    settings["TempoPercent"] = 100
    if "AllowedPlayerTracks" in settings:
        settings["PlayerTrack"] = settings["AllowedPlayerTracks"][0]
    else:
        settings["PlayerTrack"] = config.DEFAULTplayertrack
    settings["Sandbox"] = config.SANDBOXplay 

    return settings

class PieceClass:

##  PIECE CLASS

    def __init__( self, piecedir, pimidi, piecesettings ):
        ''' de piece class legt uit hoe midi gelezen en geschreven moet worden, playclass
        zorgt dat je kan spelen, edit class obviously dat je kan editen. MetaPieceClass 
        is verantwoordelijk over de pieces (liedjes) en moeilijkheidsgraad
        '''
        self.piecedir = piecedir
        self.settings = piecesettings
        self.allowedsettings = [ "Name", "Difficulty", "AllowedDifficulties",
                                 "PlayerStarts", "PlayerTrack", "BookmarkTicks",
                                 "Metronome", "Sandbox" ]

        split = os.path.split( piecedir ) # split de 'path' waardoor je een base krijgt en laatste folder
        self.settings["Name"] = split[-1] #  de laatste folder is de naam
        
        if os.path.isfile( self.piecedir ) or not os.path.isdir( self.piecedir ):
            Error("Piece "+self.piecedir+" should be a directory...")
        
        self.infofile = os.path.join( self.piecedir, "info.pkl" )       

        self.loaddifficulty( pimidi, self.settings["Difficulty"] )

    def setdifficulty( self, difficulty ):
        self.settings["Difficulty"] = difficulty
        difficultystring = str( difficulty )
        self.midifile = os.path.join( self.piecedir, self.settings["Name"]+difficultystring+".mid" )

    def loaddifficulty( self, pimidi, difficulty ):
        self.setdifficulty( difficulty )

        print "attempting to load ", self.midifile

        self.timesignatures = [ ] 
        self.tempos = [ ] # array met set-tempo event
        self.instruments = [ ] # array met instraumenten voor elk lied
        self.channels = [ ] # array met channel voor elk lied 
        self.texts = [ ] # array met naam liedjes
        self.notes = [ ]  # noten die worden bespeeld
        
        try:
            readpattern = MIDI.read_midifile( self.midifile )
            if len(readpattern) > 16:
                Error(" max 16 track")
            
            # resolutie laten matchen met de EDITresolution
            if config.EDITresolution % readpattern.resolution:
                Warn(" midi file resolutie deelt niet even met de EDITresolution ")
                resolutionmultiplier = 1.0 * config.EDITresolution / readpattern.resolution 
            else:
                resolutionmultiplier = config.EDITresolution / readpattern.resolution 
            
            self.resolution = config.EDITresolution

            for i in range(len(readpattern)):
                absoluteticks = 0
                self.notes.append( [ ] )
                self.channels.append( i+1 )
                self.instruments.append( None ) # default to PIANO instrument
                # het begin van de texts array is het naam van het lied
                trackname = MIDI.TextMetaEvent(text="")
                trackname.absoluteticks = 0
                self.texts.append( [ trackname ] )
                del trackname
                print "Track", i
                for event in readpattern[i]:
                    event.tick *= resolutionmultiplier 
                    absoluteticks += event.tick # relativetime --> absolutetime
                    event.tick = int(event.tick) # in case we were floating because of the Warning
                    if event.name == "Time Signature":
                        event.absoluteticks = int(absoluteticks) # absolute ticks van dit event
                        self.timesignatures.append( event )
                    elif event.name == "Set Tempo":
                        event.absoluteticks = int(absoluteticks) # absolute ticks van dit event
                        self.tempos.append( event )
                    elif ( event.name == "Note On"
                           or event.name == "Note Off" ): # voeg aan "notes" toe
                        event.absoluteticks = int(absoluteticks) # absolute ticks van dit event
                        self.notes[i].append( event )
                    elif event.name == "Program Change":
                        self.instruments[i] = event.value
                        self.channels[i] = event.channel
                    elif event.name == "Control Change":
                        self.channels[i] = event.channel
                    elif event.name == "Track Name":
                        trackname = MIDI.TextMetaEvent(text=event.text)
                        trackname.absoluteticks = 0
                        self.texts[i][0] = trackname
                        del trackname
                    elif event.name == "Text":
                        event.absoluteticks = int(absoluteticks) # absolute ticks van dit event
                        self.texts[i].append( event )
                    elif event.name == "End of Track":
                        pass
                    else:
                        print "unknown event", event,"on track", i

                self.setinstrument( pimidi, i, self.instruments[i] )

            # Sorteren van events
            self.sorteverything()
            self.setdefaults()

        except IOError:
            Warn("WAAR IS DE MIDI FILE??")
            self.clear()

        self.numberoftracks = len(self.notes)

    def addtrack( self ):
        absoluteticks = 0
        self.notes.append( [ ] )
        self.channels.append( len(self.notes)+1 )
        self.instruments.append( None )
        trackname = MIDI.TextMetaEvent(text="")
        trackname.absoluteticks = 0
        self.texts.append( [ trackname ] )
        self.numberoftracks += 1

    def setinstrument( self, pimidi, track, instrumindex ):
        if self.channels[track] == 9:
            print "enforcing drum-ness for track", track, "[ channel 9 ]"
        elif instrumindex == None:
            print "no instrument chosen for track", track
        else:
            print "channel for track", track, "is", self.channels[track]
            self.instruments[track] = instrumindex
            pimidi.setinstrument( self.channels[track], instrumindex )
    
    def setchannel( self, pimidi, track, channel ):
        if channel == 9:
            print "enforcing drum-ness for track", track, "[ channel 9 ]"
            self.instruments[track] = None
            self.channels[track] = channel
        else:
            self.channels[track] = channel
            print "channel for track", track, "is", channel
            pimidi.setinstrument( channel, self.instruments[track] )

##  PIECE CLASS
    def clear( self ):
        self.resolution = config.EDITresolution
        trackname = MIDI.TextMetaEvent(text="")
        trackname.absoluteticks = 0
        self.texts = [ [trackname] ]
        self.notes = [ [ ] ]
        self.instruments = [ config.DEFAULTinstrument ]
        self.channels = [ 1 ] 
        self.tempos = [ ] 
        self.timesignatures = [ ]

        self.setdefaults()

    def setdefaults( self ):
        
        if len(self.tempos) == 0:
            self.addtempoevent()
        if len(self.timesignatures) == 0:
            self.addtimesignatureevent()

        self.setcurrentticks( 0 )

    def setcurrentticks( self, absoluteticks ):
        self.loaduntilticks = absoluteticks # hoe ver we zijn in het lied
        self.currenttimesignatureindex = 0 # hoe ver we zijn met het lied
        self.currenttempoindex = 0  

        self.currentnoteindex = [0]*len(self.notes) # reset de index die bijhoudt welke noten zijn vrij zijn gekomen
                                                        #met getnoteevent


        self.currenttextsindex = [0]*len(self.texts)     #reset de index die bijhoudt welke text zijn vrij zijn gekomen
                                                        #met getnoteevent

        trackindex=0
        while trackindex < len(self.notes): # loop over the tracks
            noteindex = 0
            while noteindex < len(self.notes[trackindex]):
                # kijk of de noot op de nootindex een absolute maat heeft waar we willen beginnen
                if self.notes[trackindex][noteindex].absoluteticks >= self.loaduntilticks:
                    break
                else:
                    noteindex += 1

            self.currentnoteindex[ trackindex ] = noteindex

            textindex = 0
            while textindex < len(self.texts[trackindex]):
                #kijk of de noot op de textindex een absolute maat heeft waar we willen beginnen
                if self.texts[trackindex][textindex].absoluteticks >= self.loaduntilticks:
                    break
                else:
                    textindex += 1

            self.currenttextsindex[ trackindex ] = textindex
                
            trackindex += 1

        index = 0    
        while index < len(self.tempos):
            #kijk of de noot op de nootindex een absolute maat heeft waar we willen beginnen
            if self.tempos[index].absoluteticks >= self.loaduntilticks: 
                break

            else:
                index += 1 
        self.currenttempoindex = index
        
        index = 0    
        while index < len(self.timesignatures):
            #kijk of de noot op de nootindex een absolute maat heeft waar we willen beginnen
            if self.timesignatures[index].absoluteticks >= self.loaduntilticks:
                break
            else:
                index += 1
        self.currenttimesignatureindex = index


##  PIECE CLASS

    def primegetevents( self, tickrange ): 
        self.loaduntilticks += tickrange

    def getnoteevents( self, trackindex = 0 ):  
        startindex = self.currentnoteindex[ trackindex ]
        while ( self.currentnoteindex[trackindex] < len(self.notes[trackindex]) and
                self.notes[trackindex][self.currentnoteindex[trackindex]].absoluteticks < self.loaduntilticks ):
            self.currentnoteindex[ trackindex ] += 1

        return self.notes[trackindex][startindex:self.currentnoteindex[trackindex]]

##  PIECE CLASS

    def addtempoevent( self, tempo=120, absoluteticks=0 ):
        t = MIDI.SetTempoEvent( bpm = tempo )
        t.absoluteticks = absoluteticks

        if len(self.tempos):
            if absoluteticks > self.tempos[-1].absoluteticks:
                self.tempos.append( t )
            else:
                i = 0
                while i < len(self.tempos):
                    if absoluteticks < self.tempos[i].absoluteticks:
                        self.tempos.insert(i, t)
                        break
                    elif absoluteticks == self.tempos[i].absoluteticks:
                        self.tempos[i] = t
                        break
                    else:
                        i += 1
        else:
            self.tempos.append( t )

    def addtimesignatureevent( self, num=4, absoluteticks=0 ):
        ts = MIDI.TimeSignatureEvent( numerator=num )
        ts.absoluteticks = absoluteticks

        if len(self.timesignatures):
            if absoluteticks > self.timesignatures[-1].absoluteticks:
                self.timesignatures.append( ts )
            else: 
                i = 0
                while i < len(self.timesignatures):
                    if absoluteticks < self.timesignatures[i].absoluteticks:
                        self.timesignatures.insert(i, ts)
                        break
                    elif absoluteticks == self.timesignatures[i].absoluteticks:
                        self.timesignatures[i] = ts
                        break
                    else:
                        i += 1
        else:
            self.timesignatures.append( ts )
    
    def removetimesignatureevent( self, absoluteticks ):
        if len(self.timesignatures):
            i = 0
            while i < len(self.timesignatures):
                if absoluteticks == self.timesignatures[i].absoluteticks:
                    del self.timesignatures[i]
                    return 0
                i += 1
        return 1 
    
    def removetempoevent( self, absoluteticks ):
        if len(self.tempos):
            i = 0
            while i < len(self.tempos):
                if absoluteticks == self.tempos[i].absoluteticks:
                    del self.tempos[i]
                    return 0
                i += 1
        return 1 

##  PIECE CLASS
    def addmidinote( self, midinoteevent, trackindex = 0 ):
        if midinoteevent.absoluteticks >= 0:
            i = 0
            success = False
            while i < len(self.notes[trackindex]):
                if midinoteevent.absoluteticks < self.notes[trackindex][i].absoluteticks:
                    self.notes[trackindex].insert( i, midinoteevent )
                    success = True

                    break
                i += 1
            
            if not success:
                self.notes[trackindex].append( midinoteevent )

    def addnote( self, midinote, velocity, absticks, duration, trackindex = 0 ):  
        ''' een noot toevoegen aan de track index '''

        if absticks >= 0:
            noteon = MIDI.NoteOnEvent( tick=0, velocity=velocity, pitch=midinote )
            noteon.absoluteticks = absticks
            noteoff = MIDI.NoteOffEvent( tick=0, velocity=0, pitch=midinote )
            noteoff.absoluteticks = absticks + duration

            # nodig om te spelen 
            if absticks < self.loaduntilticks:
                self.currentnoteindex[trackindex] += 1
            if absticks+duration < self.loaduntilticks:
                self.currentnoteindex[trackindex] += 1

            i = 0
            success = False
            while i < len(self.notes[trackindex]):
                if absticks < self.notes[trackindex][i].absoluteticks:
                    self.notes[trackindex].insert( i, noteon )
                    success = True

                    break
                i += 1
            
            if not success:
                self.notes[trackindex].append( noteon )
                self.notes[trackindex].append( noteoff )
            else:
                i += 1
                success = False
                # zoeken naar waar de laatste noot heen gaat
                while i < len(self.notes[trackindex]):
                    if absticks+duration < self.notes[trackindex][i].absoluteticks:
                        self.notes[trackindex].insert( i, noteoff )
                        success = True
                        break
                        
                    i += 1

                if not success:
                    self.notes[trackindex].append( noteoff )
        else:
            print "NIET PROBEREN OM EEN NOOT TOE TE VOEGEN VOOR DE EERSTE NOOT "

    def selectnotes( self, tickrange, midirange=None, trackindex=0 ):  
        # pak notes waarbij de absoluteticks >= tickrange[0] to < tickrange[1]
        #   en bijberhoordende NoteOff ALS de pitch pitch >= midirange[0] to <= midirange[1]
        if midirange == None:
            midirange = [0,128]

        selectednotes = []
        selectedmidinotes = []
        i = 0
        while i < len(self.notes[trackindex]):
            notei = self.notes[trackindex][i]
            if ( notei.name == "Note Off" ):
                pass
            elif ( notei.absoluteticks >= tickrange[1] ):
                break
                #  notes na de tickrange worden genegeert 
            elif ( midirange[0] <= notei.pitch <= midirange[-1] ):
                # filter gebaseerd op de midirange 
                onpitch = notei.pitch
                # NoteOff pakken met de goeie pitch
                j = i + 1
                while j < len(self.notes[trackindex]):
                    notej = self.notes[trackindex][j]
                    # zoek naar de NoteOff
                    if ( notej.name == "Note Off" and notej.pitch == onpitch ):
                        if ( notei.absoluteticks >= tickrange[0]
                        or notej.absoluteticks >= tickrange[0] ):
                            # NoteOn start na tickrange[0] (maar voor  tickrange[1] 
                            selectednotes.append( [ onpitch,
                                notei.velocity,
                                notei.absoluteticks,
                                notej.absoluteticks
                                -notei.absoluteticks 
                            ] )
                            selectedmidinotes.append( notei )
                            selectedmidinotes.append( notej )
                        break
                    j += 1

            i += 1

        return selectednotes, selectedmidinotes

    def deletenotes( self, selectednotes, selectednotestrack=0 ):
        if len(selectednotes):
            ti = 0 # hou note index bij 
            si = 0 # geselecteerde note index 
            searchon = True
            while ( si < len(selectednotes) ):
                if ti >= len( self.notes[selectednotestrack] ) or ti < 0:
                    ti = 0
                    
                tracknote = self.notes[selectednotestrack][ti]
                selnote = selectednotes[si]

                if searchon:
                    name = "Note On"
                    absticks = selnote[2]
                else:
                    name = "Note Off"
                    absticks = selnote[2] + selnote[3]

                if ( tracknote.pitch == selnote[0] and 
                     tracknote.name == name and
                     tracknote.absoluteticks == absticks ):
                    del self.notes[selectednotestrack][ti]

                    if not searchon: # als we zoeken naar een NoteOff
                        si += 1     # +1 noot die we zoeken
                        ti -= 5     # -5 in het lied 
                    
                    searchon = not searchon
                else:
                    ti += 1

        self.notes[selectednotestrack].sort(key=operator.attrgetter('absoluteticks'))

        
##  PIECE CLASS

    def carveoutregion( self, tickrange, midirange=None, trackindex=0 ):  
        # verwijderd noten in dit gedeelte

        if midirange == None:
            midirange = [0,128]
        
        undeleted = [] 
        
        i = 0
        while i < len(self.notes[trackindex]):
            notei = self.notes[trackindex][i]
            if ( notei.name == "Note Off" ):
                pass
            elif ( notei.absoluteticks >= tickrange[1] ):
                break
                # NoteOn na de tickrange worden genegeerd
            elif ( midirange[0] <= notei.pitch <= midirange[-1] ):
                # filter gebaseerd op de midirange 
                # natuurlijk bij een NoteOn willen we de NoteOff ook
                onpitch = notei.pitch
                # pak de NoteOff met de juiste pitch
                j = i + 1
                while j < len(self.notes[trackindex]):
                    notej = self.notes[trackindex][j]
                    if ( notej.name == "Note Off" and notej.pitch == onpitch ):
                        if notei.absoluteticks >= tickrange[0]:
                            # NoteOn start tickrange[0]
                            if notej.absoluteticks <= tickrange[1]:
                                # NoteOn en NoteOff worden verwijderd
                                undeleted.append( [ onpitch,
                                                    notei.velocity,
                                                    notei.absoluteticks,
                                                    notej.absoluteticks
                                                    -notei.absoluteticks ] )

                                # huts
                                del self.notes[trackindex][i]
                                i -= 1 # -1 aangezien de een noot is verwijderd
                                
                                del self.notes[trackindex][j-1] # need to minus one here
                            else:
                                # NoteOff is buiten de verwijder zone
                                # oftewel NoteOn gaan naar(to tickrange[1])
                                
                                # pak wat er in de carvedout zone is 
                                undeleted.append( [ onpitch, notei.velocity,
                                    notei.absoluteticks,
                                    tickrange[1]-notei.absoluteticks
                                    -config.EDITnotespace ] )
                                
                                # NoteOn naar tickrange[1]
                                notei.absoluteticks = tickrange[1]
                        else:
                            if notej.absoluteticks <= tickrange[0]:
                                pass
                            elif notej.absoluteticks <= tickrange[1]:
                                # aangezien NoteOff buiten de range is, ga naar tickrange[0]
                                undeleted.append( [ onpitch, 
                                                    notei.velocity,  
                                                    tickrange[0], 
                                                    notej.absoluteticks - tickrange[0]  
                                                    - config.EDITnotespace
                                                  ] )
                                notej.absoluteticks = tickrange[0] - config.EDITnotespace
                            else:
                                
                                undeleted.append( [ onpitch, 
                                                    notei.velocity,  
                                                    tickrange[0], #starts at tickrange[0]
                                                    tickrange[1] - tickrange[0]  
                                                    - config.EDITnotespace
                                                  ] )
                                # ipv notes verwijderen, gaan we NoteOn and NoteOff teoveogen
                                noteoff = MIDI.NoteOffEvent( tick=0, pitch=onpitch, 
                                    absoluteticks = tickrange[0]-config.EDITnotespace )
                                self.notes[trackindex].insert( i+1, noteoff )
                                del noteoff
                                noteon = MIDI.NoteOnEvent( tick=0, pitch=onpitch, 
                                    velocity=notei.velocity,
                                    absoluteticks = tickrange[1] )
                                self.notes[trackindex].insert( i+2, noteon )
                                del noteon
                                i += 2
                        break
                    j += 1

            i += 1
        
        self.notes[trackindex].sort(key=operator.attrgetter('absoluteticks'))
        return undeleted

##  PIECE CLASS

    def deletenextonnote( self, pitch, startingticks, track=0 ):
        ti = 0 # track noot index
        while ti < len( self.notes[track] ): 
            tracknote = self.notes[track][ti]
            if ( tracknote.name == "Note On" 
            and tracknote.absoluteticks > startingticks
            and tracknote.pitch == pitch ):
                del self.notes[track][ti]
                return 0
            ti += 1
        return 1
    
    def deleteonnote( self, pitch, tickrange, track=0 ):
        ti = 0 # track noot index
        while ti < len( self.notes[track] ): 
            tracknote = self.notes[track][ti]
            if ( tracknote.name == "Note On" 
            and tickrange[0] < tracknote.absoluteticks <= tickrange[-1]
            and tracknote.pitch == pitch ):
                del self.notes[track][ti]
                return 0
            ti += 1
        return 1

    def gettimesignatureevents( self ): 
        ''' dit moet genoemd worden gelijk na getnoteevents''' 
        startindex = self.currenttimesignatureindex
        while ( self.currenttimesignatureindex < len(self.timesignatures) and
                self.timesignatures[self.currenttimesignatureindex].absoluteticks < self.loaduntilticks ):
            self.currenttimesignatureindex += 1
        
        return self.timesignatures[startindex:self.currenttimesignatureindex]
    
    def gettempoevents( self ): 
        ''' dit moet genoemd worden na getnoteevents en gettimesignatureevents'''
        startindex = self.currenttempoindex
        while ( self.currenttempoindex < len(self.tempos) and
                self.tempos[self.currenttempoindex].absoluteticks < self.loaduntilticks ):
            self.currenttempoindex += 1
        
        return self.tempos[startindex:self.currenttempoindex]

##  PIECE CLASS

    def gettextevents( self, trackindex = 0 ):
        startindex = self.currenttextsindex[ trackindex ]
        while ( self.currenttextsindex[trackindex] < len(self.texts[trackindex]) and
                self.texts[trackindex][self.currenttextsindex[trackindex]].absoluteticks < self.loaduntilticks ):
            self.currenttextsindex[ trackindex ] += 1

        return self.texts[trackindex][startindex:self.currenttextsindex[trackindex]]
        
    def addremovetextevent( self, text, absoluteticks=0, trackindex=0 ):
        ''' returns 1 als je een text event toevoegt(len(text)>0), 
        -1 als je een text event weghaald (len(text)==0),
        en 0 als niets gebeurt (len(text)==0 and geen matching tekst met absoluteticks) '''
        if absoluteticks == 0:
            # stel het naam van het lied vast als we in het begin van het lied zijn
            self.texts[trackindex][0].text = text
            if len(text):
                return 1
            else:
                return -1
        elif len(text):
            # voeg proces
            miditext = MIDI.TextMetaEvent(text=text)
            # we moeten deze data toevoegen met de hand, geen idee waarom tho
            miditext.data = [ ord(letter) for letter in text ]
            miditext.absoluteticks = absoluteticks

            if absoluteticks > self.texts[trackindex][-1].absoluteticks:
                self.texts[trackindex].append( miditext ) 
                return 1
            else:
                i = 0
                while i < len(self.texts[trackindex]):
                    if absoluteticks < self.texts[trackindex][i].absoluteticks:
                        self.texts[trackindex].insert(i, miditext)
                        return 1
                    elif absoluteticks == self.texts[trackindex][i].absoluteticks:
                        self.texts[trackindex][i] = miditext
                        return 1
                    else:
                        i += 1
        else:
            # verwijder proces
            i = 0
            while i < len(self.texts[trackindex]):
                if absoluteticks == self.texts[trackindex][i].absoluteticks:
                    del self.texts[trackindex][i]
                    return -1
                else:
                    i += 1
        return 0

##  PIECE CLASS

    def sorteverything( self ):
        ''' sorteert elke noot in elke track, ook de tempo and tijd signaturen '''
        for track in self.notes:
            track.sort(key=operator.attrgetter('absoluteticks'))
        for i in range(len(self.texts)):
            trackname = self.texts[i][0]
            tracktexts = self.texts[i][1:]
            tracktexts.sort(key=operator.attrgetter('absoluteticks'))
            self.texts[i] = [trackname] + tracktexts

        self.tempos.sort(key=operator.attrgetter('absoluteticks'))
        self.timesignatures.sort(key=operator.attrgetter('absoluteticks'))

    def writeinfo( self ):
        with open(self.infofile, 'wb') as handle:
            pickle.dump(self.settings, handle)
     
##  PIECE CLASS

    def writemidi( self, filedir="" ):
        # sorteer de events van abs ticks
        # gooit alle tracks en time signatures in track [0]

        # pak de track naam
        if self.texts[0][0].text != "":
            trackname = MIDI.TrackNameEvent(text=self.texts[0][0].text, tick=0)
            trackname.absoluteticks = 0
            # dunno werkt niet voor een of andere reden
            trackname.data = [ ]
            i = 0
            while i < len(self.texts[0][0].text):
                trackname.data.append( ord( self.texts[0][0].text[i] ) ) 
                i+= 1
            tracks = [[ trackname]] 
            del trackname # verwijderd de naam als de hierboven genoteerde naam opnieuw wordt gebruikt
        else:
            tracks = [[]]
        # gooi alles in track [0]
        tracks[0] += self.texts[0][1:] + self.tempos+self.timesignatures+self.notes[0]
        # sorteer alles
        tracks[0].sort(key=operator.attrgetter('absoluteticks'))

        # pakt de instrument
        if self.channels[0] != 9 and self.instruments[0]:
            tracks[0].insert(0, MIDI.ProgramChangeEvent( value=self.instruments[0],
                            channel=self.channels[0]  ) )

        for i in range(1,len(self.notes)):
            # sorteer de tracks
            # pak de track naam
            if self.texts[i][0].text != "":
                trackname = MIDI.TrackNameEvent(text=self.texts[i][0].text, tick=0)
                # dunno dit werkt niet voor een of andere reden
                trackname.data = [ ]
                trackname.absoluteticks = 0
                j = 0
                while j < len(self.texts[i][0].text):
                    trackname.data.append( ord( self.texts[i][0].text[j] ) ) 
                    j += 1
                tracks.append( [ trackname ] )
                del trackname # verwijderd de naam als de hierboven genoteerde naam opnieuw wordt gebruikt
            else:
                tracks.append( [] )
            # pak de instrument
            tracks[i] += self.texts[i][1:] + self.notes[i] 
            tracks[i].sort(key=operator.attrgetter('absoluteticks'))
            if self.channels[i] != 9 and self.instruments[i]:
                tracks[i].insert(0, MIDI.ProgramChangeEvent( value=self.instruments[i],
                            channel=self.channels[i] ))

        # kijk of de lokale ticks goed zijn
        tickdivisor = config.EDITresolution
        for i in range(len(tracks)):
            tracks[i].insert(0, MIDI.ControlChangeEvent( tick=0, channel=self.channels[i],
                                                        data=[7,127]) )
        for track in tracks:
            previouseventabsoluteticks = 0
            for event in track:
                try:
                    thiseventabsoluteticks = int(event.absoluteticks)
                except AttributeError:
                    thiseventabsoluteticks = 0
                # aantal ticks in vergelijking tot voorgaande ticks en current ticks
                tickmeoff = thiseventabsoluteticks - previouseventabsoluteticks
                event.tick = tickmeoff
                # om te kijken hoe klein de resolutie is
                tickdivisor = gcd( tickdivisor, tickmeoff )
                # set de ticks voor de volgende event(midi)
                previouseventabsoluteticks = thiseventabsoluteticks
         
        if config.EDITresolution % tickdivisor:
            Error(" min RESOLUTON kan niet gedeeld worden door EDITresolution.  er is iets gaande ")

        newpattern = MIDI.Pattern( resolution=config.EDITresolution/tickdivisor )
        for track in tracks:
            if tickdivisor > 1:
                for event in track:
                    # deel de relatieve ticks
                    event.tick /= tickdivisor
                    # laat abs ticks in de edit resolution
            if track[-1].name != "End of Track":
                # voeg het einde van een track hier als het er niet is
                track.append( MIDI.EndOfTrackEvent( tick=config.EDITresolution/tickdivisor ) )
            newpattern.append( MIDI.Track(track) )
        
        if filedir == "":
            MIDI.write_midifile(self.midifile, newpattern)
        else:
            MIDI.write_midifile(filedir, newpattern)
        
##  PIECE CLASS

    def gettimesignature( self, absoluteticks ):
        i = len(self.timesignatures) - 1 # begin van het begin van een lied en speel het achterwaarts
        while i >= 0:
            if self.timesignatures[i].absoluteticks <= absoluteticks:
                return self.timesignatures[i].numerator, i  # beats per opmeting
            else:
                i -= 1
        return 4, None # standaard beats per opmeting

##  PIECE CLASS

    def getfloormeasureticks( self, absoluteticks ): 
        lastchange = 0
        timesig = 4
        if len(self.timesignatures) > 0:
            i = len(self.timesignatures) - 1 # begin van het begin van een lied en speel het achterwaarts
            while i >= 0:
                if self.timesignatures[i].absoluteticks <= absoluteticks:
                    timesig = self.timesignatures[i].numerator # beats per opmeting
                    lastchange = self.timesignatures[i].absoluteticks
                    break
                else:
                    i -= 1

        relativeticks = absoluteticks - lastchange
        tickspermeasure = timesig * self.resolution # hoeveelheid ticks
        relativemeasures = int( floor( 1.0*relativeticks / tickspermeasure ) )

        return lastchange + relativemeasures * tickspermeasure
        
    def gettempo( self, absoluteticks ):
        i = len(self.tempos) - 1 # begin van het begin van een lied en speel het achterwaarts
        while i >= 0:
            if self.tempos[i].absoluteticks <= absoluteticks:
                return self.tempos[i].bpm
            else:
                i -= 1
        return 120 # standaard tempo

        
##  END PIECE CLASS

if __name__ == "__main__":
    from pimidi import *
    PImidi = MidiClass()
    piece = PieceClass("songs/Random/Polka/Fish Polka", 
                        PImidi,
                        {"Difficulty" : 5, 
                         "Name" : "Fish Polka", 
                         "PlayerStarts" : True, 
                         "PlayerTrack" : 3 } )

    piece.writemidi( "fishy.mid" )
    #print piece.notes[5]
    

