# pimidi.py - voor midi input van je keyboard en soundfont voor geluid.
import pygame
import pygame.midi
from mingus.midi import fluidsynth
import config
import os

class MidiClass:
    def __init__( self ):

        if not fluidsynth.init( os.path.join( config.RESOURCEdirectory, config.SOUNDfont), 
            config.FLUIDSYNTHdriver ):
            sys.exit(" Kan de Fluidsynth Sountfont PianoMenu.sf2 niet laden ")
        # Een instrument geven aan je channels.  
        fluidsynth.set_instrument( config.PIANOchannel,    ## channel voor je instrument.
                                   config.SOUNDfontPIANO ) ## instrument gebaseerd op je soundfont.

        self.keysmod12 = [ "C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B" ]
        self.keyson = [ 0 ]*12  # Representeert alle keys in een octaaf
        self.newnotesonlist = [ ]   # lijst van de noten die de gebruiker heeft aangeslagen.
        self.newnotesofflist = [ ]  # Lijst van noten die gebruiker loslaat.
        #self.noteson = set()    # noten die gebruiker gebruikt. 
        self.pitchwheel = 64    
        self.modwheel = 0       
        self.transientnotes = []
        pygame.midi.init()

    def playnote( self, midinote, notevel=100, duration=1, channel=0 ):
        ''' speelt een note voor een kortdurende tijd '''
        self.transientnotes.append( [ midinote, duration, channel ] )
        fluidsynth.play_Note( midinote, channel, notevel ) # 

    def startnote( self, midinote, notevel=100, channel=0 ):
        ''' start een note vanuit een midi apparaat, je moet het zelf eindigen!. '''
        fluidsynth.play_Note( midinote, channel, notevel ) # 

    def endnote( self, midinote, channel=0 ):
        ''' Dit stopt de note '''
        fluidsynth.stop_Note( midinote, channel ) # stop  note

    def clearall( self ):
        fluidsynth.stop_everything()
    
    #Dit leest je midi apparaat in de settings zodat je het in gebruik kan nemen.
    def getallowedinputs(self):            
        allowedin = []
        allowedinnames = []
        for midi_id in range( pygame.midi.get_count() ):
            interface, name, input, output, opened = pygame.midi.get_device_info( midi_id )
            if input:
                allowedin.append( midi_id )
                allowedinnames.append( name )

        return allowedin, allowedinnames
    
    #Geeft een channel aan de isntrument van je soundfont.
    def setinstrument( self, channel, instrument ):
        fluidsynth.set_instrument( channel, instrument )
        print "setting channel", channel, "to instrument", instrument

    def setinput( self, midi_id ):
        try:
            del self.midiin
        except AttributeError:
            pass

        self.midiin = pygame.midi.Input( midi_id )

    def update( self, dt ):
        ## checkt of er enige midi processen zijn.
        if self.midiin.poll():
            midi_events = self.midiin.read(10)
            # convert naar pygame events
            midi_evs = pygame.midi.midis2events(midi_events, self.midiin.device_id)

            for m_e in midi_evs:
                pygame.fastevent.post( m_e )
        
        i=0
        while i < len(self.transientnotes):
            self.transientnotes[i][1] -= dt
            if self.transientnotes[i][1] < 0:
                fluidsynth.stop_Note( self.transientnotes[i][0], self.transientnotes[i][2] ) # stop note
                del self.transientnotes[i]
            else:
                i += 1
     
    #Midi naar pygame events worden hieronder uitgeschreven.
    def process( self, event ):
        if event.type in [pygame.midi.MIDIIN]:
            octave, numnote = divmod(event.data1, 12)
            #note = self.keysmod12[numnote]  # "returns" de noten in taal, dus "C, D, E" etc.
            if event.status == 144: #key ingeklikt
                velocity = event.data2
                self.keyson[numnote] += 1
                self.newnotesonlist.append( [event.data1, event.data2] ) #note en velocity
                #self.noteson.add( event.data1 )
            elif event.status == 128: #key up
                self.newnotesofflist.append( event.data1 ) #note en velocity
                if self.keyson[numnote] > 0:
                    self.keyson[numnote] -= 1
                #self.noteson.remove( event.data1 )
            elif event.status == 224: #pitch wheel
                self.pitchwheel = event.data2 # is standaard pitch op 64, maar kan van 0 to 127
            elif event.status == 176: #mod wheel
                self.modwheel = event.data2 #ergens tussen 0 en 127  
            ## dit was een midi event.
            return 1
        else:
            ## dit was geen midi event.
            return 0

    def newnoteson(self):
        newonlist = self.newnotesonlist
        self.newnotesonlist = []
        return newonlist
    
    def newnotesoff(self):
        newofflist = self.newnotesofflist
        self.newnotesofflist = [] 
        return newofflist

    def quit(self):
        del self.midiin
        pygame.midi.quit()
