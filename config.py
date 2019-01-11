# Belangrijke geluid instellingen.
# en hoe je fluidsynth werkend krijgt.  
FLUIDSYNTHdriver = "alsa"
# lijst van mogelijkheden(bij ons werkt alleen alsa, de rest doet raar of wordt helemaal niet herkend):
# 'alsa', 'oss', 'jack', 'portaudio', 'sndmgr', 'coreaudio' or 'Direct Sound'
# ( see https://code.google.com/p/mingus/wiki/tutorialFluidsynth )
# Om PiKey werkend te krijgen heb je python mingus nodig..

# display instellingen
# display resolutie
DEFAULTresolution = (960,540)

# lengte/grootte van de zwarte/witte keys.
WHITEKEYfraction = 0.13 # grootte verticale scherm
BLACKKEYwhitefraction = 0.7 # grootte van de piano keys
NOTEwidth = 20
KEYwidth = 50
# hoe groot de "balken" zijn(verticaal):
PIXELSperbeat = 100     # dit mag je verlagen als je een lage resolutie hebt.
FONT = "monospace" # hier kan je je eigen font kiezen.
FONTSIZEmultiplier = 1  # dit moet je veranderen naar 1.5 of 2 als je een lage resolutie hebt.
DIVIDERcolor = (100,120,80)
MEASUREcolor = (10,0,10)
# je hebt hier 5 helper lines:
HELPERLINEmax = 5
# cursor kleur:
CURSORcolor = (100,250,250)
# voor kleine schermen heb je ook kleine notificaties nodig:
SMALLalerts = False

# uitgesloten display settings.

# Waar kan je de songs vinden:
PIECEdirectory = "songs"
# Waar kan je resources vinden:
RESOURCEdirectory = "resources"

# MEER GELUID INSTELLINGEN

# metronome click track instellingen.
METRONOMEdefault = False    # wel of geen mentronome track, metronome track.
CLICKTRACKvolume = 0.05     # nummer tussen 0 en 1, volume van een ingeklikte knop.

# octave noten van de soundfont
LOWESTnote = 9      # dit is meestal 21 (lage A op de piano)
HIGHESTnote = 96    # dit is meestal 108   (hoge C op de piano)

# instrument soundfont(piano):  gekopiërt van /usr/share/sounds/sf2/FluidR3_GM.sf2:
SOUNDfont = "FluidR3_GM.sf2"  # plaats dit in je resource directory nadat je de github zip heb gedownload en hebt uitgepakt.
# Als je andere instrumenten wil kan je ze instellen, wat je dan moet veranderen zijn de nummers die ze aangeven dus ipv piano(0, 1) doe je dan 2 voor honky tonk piano.
# 0, 1 = piano
# 2 = honky tonk piano
# 3 = tacky piano
# 4,5 = electric piano
# ... zie http://en.wikipedia.org/wiki/General_MIDI#Program_change_events
# 124 = telephone
# 125 = helicopter
# 126 = water??
# 127 = gunshot
SOUNDfontPIANO = 1
SOUNDfontORGAN = 19
SOUNDfontHONKY = 2

INSTRUMENT = { 
    "drums" : "drums",  # drums hebben hun aparte channel
    "piano" : 1,
    "organ" : 19,
    "epiano" : 4,
    "bass" : 33,    # bass is alles tussen 32 en 39
    "violin" : 40,
    "viola" : 41,
    "cello" : 42,
    "whistle" : 78,
    "ocarina": 79,
    "square" : 80,
    "saw" : 81,
    "voice" : 85,
    "choir" : 91
}

# standaard channel piano:
PIANOchannel = 0

# standaard instrument
DEFAULTinstrument = 0


# play mode instellingen
SANDBOXplay = 1 # standaard bij zowel geen als wel sandbox mode.
DEFAULTdifficulty = 0

# PIANO KEYBOARD INSTELLINGEN, kleur etc.
# Kleuren van de noten die je intikt.
#               C           C#        D         Eb              E           F
rainbow = [ (255,0,0), (245, 40, 0), (210,80,0), (190,130,0), (220,220,0), (140,228,0), 
            (0,240,0), (0,159,199), (0,55,248), (33,0,252), (114,0,228), (180,0,180) ]
#               F#          G           Ab          A           Bb          B
#kleuren kan je altijd veranderen alleen heb je dan hun code nodig dus (255,0,0) moet dan veranderd worden.

# Edit instellingen
COMMANDhistory = 100 # cmd max up/down dat je kan doen is 100
# dit zijn de standaard composities
# en pak de tempo van een track.
PLAYERstarts = True # is true als het piano stukjes zijn en FALSE als er achtergrond muziek is.
ALLOWEDplayertracks = [0] # welke track de speler moet spelen. 
ALLOWEDdifficulties = [0] # moeilijksheidgraden aka "level mode"
TEMPO = 120 # standaard tempo
DEFAULTplayertrack = 0

# ---------------------------------------------------------------------------------------------
# it is not recommended to mess with the following, but you can if you know what you're doing:
# resolution = # of ticks per beat.  
EDITresolution = 5040   # (1 * 2 * 3 * 2 * 5 * 7 * 2 * 3 * 2 * 2 * 2)/4 
                        # if EDITresolution = 5040, and if there are four beats per measure,
                        # this means we can represent these various notes by these numbers of ticks:
                        # NOTE            # TICKS
                        # whole            20,160
                        # half             10,080
                        # third             6,720
                        # quarter           5,040
                        # fifth             4,032
                        # quarter-triplets  3,360
                        # seventh           2,880
                        # eighth            2,520
                        # sixteenth         1,260
                        # thirty-secondth     630
                        # sixty-fourth        315
                        # and many others in between.
EDITshortestnote = 315  # shortest note you want to allow, in ticks.
EDITnotespace = 20 # # of ticks to give white-space letting a note go and hitting the next
#-----------------------------------------------------------------------------------------------

# GAME variable, dit moet zo blijven!
# GAMESTATEexit = 0 # Verlaat game, DIT MOET 0 ZIJN!
GAMESTATEplay = 1 # speelt een stuk(lied)
GAMESTATEpiecesettings = 2  # instellingen voor tempo, stukjes etc.
GAMESTATEpieceselection = 3 # hier kan je je stuk(piece) kiezen in de piecedirectory.
GAMESTATEmainmenu = 4 # main menu
GAMESTATEsettings = 5 # instellingen menu
GAMESTATEeditmenu = 6 # menu om te kiezen welke stuk(piece) je wilt editten.
GAMESTATEedit = 7 # editten en maken van stukjes(pieces)
