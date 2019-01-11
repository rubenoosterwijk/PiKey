# this is the meta-gameplay for both the play and edit classes.
#
# ddrstyle  :   De noten vallen vanaf de bovenkant van scherm naar beneden
#           :   Om punten te scoren, tik je de juiste toets in wanneer hij
#           :   aan de onderkant van het scherm is
#
from metagame import *
from backdrops import *
from pimidi import *
from piece import *
import config
#
from collections import deque  # Dit gebruiken we om te voorkomen dat er teveel lists in de wacht worden gezet


def divisors(n):
    # Hiermee gaan we de priemgetallen vaststellen
    # thanks to Ben Ruijl on
    # http://stackoverflow.com/questions/12421969/finding-all-divisors-of-a-number-optimization

    # first factorize n
    factors = []
    # gebruik alleen de eerste paar priemgetallen om te ontbinden in factoren
    for p in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61]:
        if p * p > n: break
        i = 0
        while n % p == 0:
            n //= p
            i += 1
        if i > 0:
            factors.append((p, i));
    if n > 1: factors.append((n, 1))

    # nu we de factoren hebben, sorteren we de delers van klein naar groot
    div = [1]
    for (p, r) in factors:
        div = [d * p ** e for d in div for e in range(r + 1)]

    div.sort()
    return div


class DDRClass(GameChunkClass):
    def __init__(self, piecedir, midi,
                 piecesettings={
                     "BookmarkTicks": [],
                     "TempoPercent": 100, "Difficulty": 0,
                     "Sandbox": config.SANDBOXplay,
                     "PlayerStarts": config.PLAYERstarts,
                     "PlayerTrack": 0,
                     "Metronome": config.METRONOMEdefault}):
        ''' the DDR class interfaces between a piece and the visuals onscreen. '''
        self.backdrop = ColorOscillatingBackDropClass()
        self.alerttext = ""
        self.alerttimer = 0
        self.previousabsoluteticks = 0

        # het merendeel van het werk gebeurt in de volgende class genaamd KeyboardAndMusicVisualsClass...
        # die aan de onderkant van deze ddr file staat. Dit is hoe we de noten visualiseren en het balkensysteem genereren
        # het bevat het visuele van:
        self.keymusic = KeyboardAndMusicVisualsClass()
        self.keymusic.metronome = piecesettings["Metronome"]

        # the DDRClass is in feite een interface tussen het product en het visuele.
        self.piece = PieceClass(piecedir, midi, piecesettings)

        self.currenttrack = piecesettings["PlayerTrack"]
        # het product toont alles in midi noten,
        # maar het visuele kent alleen pixels en dat moeten we dus omzetten
        self.resolution = self.piece.resolution
        self.tempomultiplier = 1.0 * piecesettings["TempoPercent"] / 100
        self.sandbox = piecesettings["Sandbox"]
        self.noisytracks = set(range(self.piece.numberoftracks))
        self.bookmarkticks = self.piece.settings["BookmarkTicks"]

        # nu stellen we het tijd schema op, met de toegestane tijdsduur
        # bijvoorbeeld, met een X / 4 (bijvoorbeeld 6/4, 3/4, 4/4) ,

        # krijgt de kwartnoot de tel.
        # hier vinden we in welke tijdsduren onze beatnotitie kan verdelen:
        self.allowedbeatdivisors = divisors(self.resolution)  # standaard is 5040

        # resolution = # aantal tikken per beat.  1 tik is de kleinste tijdseenheid in een midi file,
        # maar de exacte tijdsduur in seconden hangt af van het tempo en de resolution.
        # MIDI gebruikt microseconden om van een tempo in bpm (beats per minute) naar tijdseenheid van time per beat te gaan.
        # 1 tik * (1,000,000 microseconden/seconden) * (60 sec/min) / (tempo [bpm]) / resolution [ticks/beat]
        # = 60,000,000/(Tempo*Resolution) microseconden,
        # wat gelijkstaat aan precies 60,000,000/(Tempo*Resolution) microseconds / tick.

        # beperk de toegestane duur zodat we geen miniscule eenheden krijgen in ons tijdschema.
        i = 1  # je hoeft niet te starten bij i=0,  allowedbeatdivisors[0] = 1.
        while i < len(self.allowedbeatdivisors):
            if self.allowedbeatdivisors[i] > 16:  # de standaard is 16.
                del self.allowedbeatdivisors[i:]  # sta alleen een duur tot max MAXbeatDIVISOR toe
                # if MAXbeatDIVISOR = 16 en de kwartnoot valt op de beat
                # betekent het dat 64 noten het kleinst aantal toegestane noten is.
                # Maar dat is alleen als EDITresolution precies door 16 te verdelen is.
                break
            else:
                i += 1

        # duur van het tijdsschema toename (de huidige lengte van 1 noot)
        self.readnotecode("b")
        # het bovenstaande bepaald self.notecode:
        # self.notecode = "n"    # 1n 2n 3n, ..., n/1, n/2, n/3, ...  "note" (beat)
        # 1m 2m 3m, ..., m/1, m/2, m/3, ...  "measure"
        self.currentnoteoffset = 0

        # in feite bepalen we de noten op basis van hun rijk aan maximum tikken.
        # we load in a full screen at a time
        # except when resetting everything, when we load in an extra screen to be safe.
        self.currentabsoluteticks = 0
        self.setcurrentticksandload(0)

        self.play = False  # zet de standaard op 'niet direct spelen'.  Dit staat vast in afgeleide classes
        self.selectednotes = []
        self.looping = False
        self.loopingbookmarkindex = 0

    def readnotecode(self, notecode):
        # probeer de noot duur te vinden gebasseerd op de notecode
        notecode = notecode.replace(" ", "")  # verwijder spaties
        nindex = notecode.find("b")
        notemultiplier = 1
        notedivider = 1
        notebase = "b"  # zet een standaard op 1 beat
        warning = False
        if nindex >= 0:
            # "b" is in notecode:
            if len(notecode) > 1:
                if nindex > 0:
                    try:
                        notemultiplier = int(notecode[:nindex])
                    except:
                        warning = True
                # print "note mult = ", notemultiplier
                divideindex = notecode.find("/")
                if divideindex < 0:
                    # geen verdeler
                    pass
                elif divideindex > nindex:
                    try:
                        notedivider = int(notecode[divideindex + 1:])
                    except:
                        warning = True
                else:
                    warning = True
            else:
                # dit is standaard.
                # notecode = "b" -> notebase = "b", notemultiplier, notedivider = 1
                pass
        else:
            # "n" is NIET in notecode.
            mindex = notecode.find("m")
            if mindex >= 0:
                # "m" is wel in notecode
                notebase = "m"  #
                if len(notecode) > 1:
                    if mindex > 0:
                        try:
                            notemultiplier = int(notecode[:mindex])
                        except:
                            warning = True
                    divideindex = notecode.find("/")
                    if divideindex < 0:
                        # geen deler
                        pass
                    elif divideindex > mindex:
                        try:
                            notedivider = int(notecode[divideindex + 1:])
                        except:
                            warning = True
                    else:
                        warning = True
            else:
                # "m" is niet in notecode.
                warning = True

        if not warning:
            self.notecode = notecode
            self.notemultiplier = notemultiplier
            self.notedivider = notedivider
            self.notebase = notebase
            # return true als het een geldige note code was
            return 1
        else:
            return 0

    def getticks(self, timesignature):
        notebaseduration = self.resolution  # zet standaard op kwartnoot (bijv. een beat)
        if self.notebase == "m":  # een meting moet worden vermenigvuldigt met timesignature:
            notebaseduration *= timesignature

        noteticks = 1.0 * self.notemultiplier * notebaseduration / self.notedivider

        if self.currentnoteoffset:
            noteoffset = noteticks / 2
        else:
            noteoffset = 0

        return noteticks, noteoffset

    def resetticks(self):
        self.lastloadedtimesignature = self.currenttimesignature
        self.lastloadednoteticks, self.lastloadednoteoffset = self.getticks(self.lastloadedtimesignature)
        self.currentnoteticks = self.lastloadednoteticks

    #### DDR CLASS

    def tickstosecs(self, duration):
        # zet de duur in tikken om in seconden
        return duration * 1.0 / (self.currenttempo * self.tempomultiplier)

    def roundtonoteticks(self, absoluteticks, gobackwards=0):
        # HELP:  Gebruik "getticks("timesig") bij de absoluteticks
        ts, tsindex = self.piece.gettimesignature(absoluteticks)
        noteticks, noteoffset = self.getticks(ts)
        if absoluteticks < noteoffset:
            return noteoffset

        lastmeasure = self.piece.getfloormeasureticks(absoluteticks - noteoffset) + noteoffset

        relativeticks = absoluteticks - lastmeasure
        relativedivs = int(round(1.0 * relativeticks / noteticks)) - gobackwards
        #heeft eerst meerdere keren langs een bepaald aantal maatregelen nodig na de laatste wijziging.
        possibleticks = lastmeasure + relativedivs * noteticks

        if len(self.piece.timesignatures) > 1:
            if ((tsindex > 0
                 and possibleticks < self.piece.timesignatures[tsindex].absoluteticks)
                    or (tsindex < len(self.piece.timesignatures) - 1
                        and possibleticks >= self.piece.timesignatures[tsindex + 1].absoluteticks)
            ):
                return self.roundtonoteticks(possibleticks)

        return possibleticks

    def setcurrenttimesignature(self, timesig):
        if timesig != self.currenttimesignature:
            self.currenttimesignature = timesig

    def setcurrentticksandload(self, absoluteticks, dontround=True):
        ''' this method erases all current notes and sets the current position to absoluteticks'''
        if absoluteticks < 0:
            absoluteticks = 0
            if not dontround:
                self.currentnoteoffset = 0
        elif not dontround:
            # we moeten afronnden maar checken eerst op uitlopers
            newabsoluteticks = self.roundtonoteticks(absoluteticks)
            oldoffset = self.currentnoteoffset

            ts, index = self.piece.gettimesignature(newabsoluteticks)
            noteticks, noteoffset = self.getticks(ts)
            if newabsoluteticks > absoluteticks:
                if newabsoluteticks - absoluteticks < 0.25 * noteticks:
                    self.currentnoteoffset = 0
                else:
                    self.currentnoteoffset = 0.5 * noteticks
            elif newabsoluteticks < absoluteticks:
                if absoluteticks - newabsoluteticks < 0.25 * noteticks:
                    self.currentnoteoffset = 0
                else:
                    self.currentnoteoffset = 0.5 * noteticks
            else:
                self.currentnoteoffset = 0

            if oldoffset != self.currentnoteoffset:
                # wees er zeker van dat we afronden naar de dichtstbijzijnde tick offset
                absoluteticks = self.roundtonoteticks(absoluteticks)
            else:
                # anders was de oude afronding goed
                absoluteticks = newabsoluteticks

        # alles wissen   zx,
        self.keymusic.clearallmusic()
        self.readynotes = []
        for i in range(len(self.piece.notes)):
            self.readynotes.append(deque([]))
        # Hiervoor:  self.readynotes = [deque([])]*len(self.piece.notes)

        self.clearmidi = True
        # Bemachtig tempo en tijd signatures...
        self.currenttempo = self.piece.gettempo(absoluteticks)
        self.currenttimesignature, tsindex = self.piece.gettimesignature(absoluteticks)
        # Bemachtig de duur van de tikken
        self.resetticks()
        # vind laatst gemeten locatie, om in te laden
        self.lastloadedmeasureticks = self.piece.getfloormeasureticks(absoluteticks)
        # kleinere balken die over het scherm gaan
        self.lastloadedbarticks = self.lastloadednoteoffset

        # krijg hoe we bij de pixelcoördinaten komen
                        self.pixelspertick = (1.0 * config.PIXELSperbeat /
                              (0.6 * self.lastloadednoteticks + 0.4 * self.resolution) /
                              (0.8 + 0.2 * self.tempomultiplier)
                              )
        # en terug, hoeveel tikken we moeten laden op basis van hoe groot het scherm is:
        self.tickrange = int(2 * config.DEFAULTresolution[1] / self.pixelspertick)

        # reset absoluteticks in DDR en in piece
        self.currentabsoluteticks = absoluteticks
        self.piece.setcurrentticks(absoluteticks)

        # hier laden we de waarde van het schermhoogte
        self.loadeduntil = absoluteticks
        self.loadmusic()
        # hier laden we een andere waarde van het schermhoogte, als een buffer
        self.loadmusic()

    def loadmusic(self):
        ''' this method adds notes that are up to be looked at... '''
        # krijg alle noten van piece in een bepaalde rijk voor de spelers lied
        # en maak ze visueel
        # houd bij hoeveel we visueel maken hier
        self.loadeduntil += self.tickrange

        # start met noten:
        # begin piece voor 'getting events'
        self.piece.primegetevents(self.tickrange)

        # verkrijg de noten van elk lied
        for i in range(len(self.piece.notes)):
            events = self.piece.getnoteevents(i)
            if i == self.currenttrack:
                for note in events:
                    reltickpixels = (note.absoluteticks - self.currentabsoluteticks) * self.pixelspertick
                    if note.name == "Note On":
                        self.keymusic.addnote(note.pitch, note.velocity, reltickpixels)

                        self.readynotes[i].append([note.pitch, note.velocity, note.absoluteticks])

                    elif note.name == "Note Off":
                        self.keymusic.addnote(note.pitch, 0, reltickpixels)
                        self.readynotes[i].append([note.pitch, 0, note.absoluteticks])

            else:
                # zet de computers noten klaar
                for note in events:
                    if note.name == "Note On":
                        self.readynotes[i].append([note.pitch, note.velocity, note.absoluteticks])
                    elif note.name == "Note Off":
                        self.readynotes[i].append([note.pitch, 0, note.absoluteticks])

        # Ga door met de metingen
        tickspermeasure = self.lastloadedtimesignature * self.resolution

        if tickspermeasure % self.lastloadednoteticks == 0:
            # noot gelijkmatig verdelen over de meting 
            nextbigbar = self.lastloadedmeasureticks
            nextsmallbar = self.lastloadedbarticks

            while nextbigbar < self.loadeduntil or nextsmallbar < self.loadeduntil:
                if abs(nextbigbar - nextsmallbar) < 2:
                    # zowel de meetbalk en een balk voor de tikken moet worden geplaatst
                    # Voor nu plaatsen we eerst alleen de meetbalk.
                    nextsmallbar = nextbigbar  # reset smallbar als het niet meer synchroon loopt
                    if nextbigbar >= self.currentabsoluteticks:
                        self.keymusic.addmeasurebar(
                            (nextbigbar - self.currentabsoluteticks) * self.pixelspertick
                        )
                    # verhoog beide:
                    nextsmallbar += self.lastloadednoteticks
                    nextbigbar += tickspermeasure
                elif nextbigbar < nextsmallbar:
                    # hier zetten we de meetbalk
                    if nextbigbar >= self.currentabsoluteticks:
                        self.keymusic.addmeasurebar(
                            (nextbigbar - self.currentabsoluteticks) * self.pixelspertick
                        )
                    nextbigbar += tickspermeasure
                else:
                    # de balk voor de tikken is de volgende die geplaatst wordt:
                    if nextsmallbar >= self.currentabsoluteticks:
                        self.keymusic.addmeasurebar(
                            (nextsmallbar - self.currentabsoluteticks) * self.pixelspertick,
                            True  # om een kleine te plaatsen
                        )
                    nextsmallbar += self.lastloadednoteticks
        else:
            # nootverdeling NIET gelijkmatig verdelen
            nextbigbar = self.lastloadedmeasureticks
            nextsmallbar = self.loadeduntil
            while nextbigbar < self.loadeduntil:
                if nextbigbar >= self.currentabsoluteticks:
                    self.keymusic.addmeasurebar(
                        (nextbigbar - self.currentabsoluteticks) * self.pixelspertick
                    )
                nextbigbar += tickspermeasure

        # Nu de tijd notaties
        events = self.piece.gettimesignatureevents()
        if len(events) > 0:
            for event in events:
                # We hebben net een tijdsnotatie zien verschijnen
                newtimesig = event.numerator
                newtickspermeasure = newtimesig * self.resolution
                timesigpix = (event.absoluteticks - self.currentabsoluteticks) * self.pixelspertick
                # Voeg de tijdsnotatie ALTIJD aan keymusic.
                self.keymusic.addtimesignature(timesigpix, newtimesig)

                # Verwijder alles als de nieuwe teller anders is dan de oude
                if tickspermeasure != newtickspermeasure:
                    tickspermeasure = newtickspermeasure

                    self.lastloadedtimesignature = newtimesig
                    # update nootcompensatie en nootduur:
                    self.lastloadednoteticks, self.lastloadednoteoffset = self.getticks(newtimesig)

                    # en verwijder de meetbalken vanaf dan:
                    self.keymusic.clearmeasurebarsafter(timesigpix)

                    # en reset de lastmeasure tot dat punt zodat we die metingen kunnen toevoegen
                    # herlaad de meetbbalken hierna
                    # nieuwe verdeling markeren

                    if tickspermeasure % self.lastloadednoteticks == 0:
                        # nootverdeling gelijkmatig verdelen over de meting
                        nextbigbar = event.absoluteticks
                        nextsmallbar = nextbigbar + self.lastloadednoteoffset
                        while nextbigbar < self.loadeduntil or nextsmallbar < self.loadeduntil:
                            if abs(nextbigbar - nextsmallbar) < 2:
                                # zowel een meetbalk als een balk voor de tikken moet worden gemaakt
                                # maar we plaatsen nu alleen de meetbalk.
                                nextsmallbar = nextbigbar  # reset de kleine balk als hij niet meer synchroon loopt
                                if nextbigbar >= self.currentabsoluteticks:
                                    self.keymusic.addmeasurebar(
                                        (nextbigbar - self.currentabsoluteticks) * self.pixelspertick
                                    )
                                # verhoog beide:
                                nextsmallbar += self.lastloadednoteticks
                                nextbigbar += tickspermeasure
                            elif nextbigbar < nextsmallbar:
                                # de meetbalk moet nu geplaats worden.
                                if nextbigbar >= self.currentabsoluteticks:
                                    self.keymusic.addmeasurebar(
                                        (nextbigbar - self.currentabsoluteticks) * self.pixelspertick
                                    )
                                nextbigbar += tickspermeasure
                            else:
                                # de ballk voor de tikken wordt nu geplaatst:
                                if nextsmallbar >= self.currentabsoluteticks:
                                    self.keymusic.addmeasurebar(
                                        (nextsmallbar - self.currentabsoluteticks) * self.pixelspertick,
                                        True  # om een kleine balk te maken
                                    )
                                nextsmallbar += self.lastloadednoteticks
                    else:
                        # nootverdeling NIET gelijkmatig over de metingen verdelen
                        nextbigbar = self.lastloadedmeasureticks
                        nextsmallbar = self.loadeduntil
                        while nextbigbar < self.loadeduntil:
                            if nextbigbar >= self.currentabsoluteticks:
                                self.keymusic.addmeasurebar(
                                    (nextbigbar - self.currentabsoluteticks) * self.pixelspertick
                                )
                            nextbigbar += tickspermeasure

        self.lastloadedmeasureticks = nextbigbar
        self.lastloadedbarticks = nextsmallbar

        # Nu verkrijgen we de tempo events
        events = self.piece.gettempoevents()
        for event in events:
            # we hebben zojuist een tempo event verkegen
            self.keymusic.addtempo((event.absoluteticks - self.currentabsoluteticks) *
                                   self.pixelspertick, self.tempomultiplier * event.bpm)

        # verkrijg nu alle text events
        events = self.piece.gettextevents(self.currenttrack)
        for event in events:
            # we hebben net  een text event verkregen
            self.keymusic.addtext((event.absoluteticks - self.currentabsoluteticks) *
                                  self.pixelspertick, event.text)

    def scoochforward(self, bigscooch=False):
        if bigscooch:
            beats = 4.0
        else:
            beats = 1.0
        self.setcurrentticksandload(
            self.roundtonoteticks(beats * self.currentnoteticks + self.currentabsoluteticks)
        )

    def scoochbackward(self, bigscooch=False):
        if bigscooch:
            beats = 4.0
        else:
            beats = 1.0
        self.setcurrentticksandload(
            self.roundtonoteticks(-beats * self.currentnoteticks + self.currentabsoluteticks)
        )

    def update(self, dt, midi):
        self.backdrop.update(dt)
        self.keymusic.update(dt)

        if self.clearmidi:
            midi.clearall()
            self.clearmidi = False

        if self.alerttext:
            # als er een bericht is,
            if self.alerttimer > 0:
                # tel af
                self.alerttimer -= dt
            else:
                # sluit af
                self.alerttext = ""

        if self.play:
            # vergrijp huidige piece spul
            self.currenttimesignature, tsindex = self.piece.gettimesignature(self.currentabsoluteticks)
            self.currenttempo = self.piece.gettempo(self.currentabsoluteticks)
            # stuur de noten in balken naar beneden.
            # dt is in milliseconds.  tempo = beats per minute.  vervanging van de metingen in de tikken.
            # ticks = [ticksperbeat] * [beats per minute] * (1 minute / 60,000 milliseconds) * dt
            tickchange = dt * self.resolution * self.tempomultiplier * self.currenttempo / 60000
            self.keymusic.displaceallmusic(tickchange * self.pixelspertick)
            self.currentabsoluteticks += tickchange

            if self.looping and self.currentabsoluteticks >= self.bookmarkticks[self.loopingbookmarkindex + 1]:
                self.setcurrentticksandload(self.bookmarkticks[self.loopingbookmarkindex])
                self.setalert("Looped back to bookmark " + str(self.loopingbookmarkindex))

            else:
                # niet loopen, of we gaan normaal door
                # check of er noten gespeeld moeten worden (of gespeeld door de speler, in play-mode)
                for i in range(len(self.readynotes)):
                    track = self.readynotes[i]
                    # als de eerste noot zijn absolute tikken minder is dan de huidige absolute tikken
                    # track is een lijst met noten, elke noot is [ pitch, velocity, absoluteticks ]
                    while len(track) and (track[0][-1] <= self.currentabsoluteticks):
                        soundme = track.popleft()
                        if i in self.noisytracks:
                            if soundme[1]:  # als er velocity (snelheid) is doe:
                                midi.startnote(soundme[0], soundme[1], self.piece.channels[i])
                            else:
                                midi.endnote(soundme[0], self.piece.channels[i])

                                # Neem de noten aan die nog steeds komen
                if self.currentabsoluteticks > self.loadeduntil - self.tickrange:  # blijf twee stappen voor
                    self.loadmusic()

    def process(self, event, midi):
        if event.type == pygame.KEYDOWN:
            if event.key == 27:  # escape key
                return {"gamestate": 0, "printme": "ESCAPE FROM DDR MODE"}
            elif self.commonnav(event, midi):  # check voor gemeenschappelijke navigaties
                return {}
            elif self.commongrid(event, midi):  # check voor gemeenschappelijke navigaties
                return {}

        return {}

    def getlastmeasureticks(self):
        if len(self.piece.notes[self.currenttrack]):
            lastnoteticks = self.piece.notes[self.currenttrack][-1].absoluteticks
            return self.piece.getfloormeasureticks(lastnoteticks)
        else:
            return 0

    def commonnav(self, event, midi):
        if event.key == pygame.K_w:
            self.setalert(
                "Playing track " + str(self.currenttrack) +
                " on difficulty " + str(self.piece.settings["Difficulty"]))
            print
            "ready ", self.readynotes
            print
            "selecting ", self.selectednotes
        elif event.key == pygame.K_h or event.key == pygame.K_LEFT:  # druk links
            if pygame.key.get_mods() & pygame.KMOD_SHIFT:  # als de shifttoets is ingedrukt
                self.keymusic.scoochkeyboard(-6)
            else:
                self.keymusic.scoochkeyboard(-1)
            return 1
        elif event.key == pygame.K_l or event.key == pygame.K_RIGHT:  # druk rechts
            if pygame.key.get_mods() & pygame.KMOD_SHIFT:  # als de shifttoets is ingedrukt
                self.keymusic.scoochkeyboard(6)
            else:
                self.keymusic.scoochkeyboard(1)
            return 1

        # andere  gebeurtenissen zijn alleen toegestaan in de sandbox mode
        elif self.sandbox:
            if event.key == pygame.K_SPACE:
                if self.play and self.looping:
                    # spring terug naar het begin als we aan loopen waren
                    self.currentabsoluteticks = self.bookmarkticks[self.loopingbookmarkindex]
                self.looping = False  # standaard om te stoppen met loopen.
                midi.clearall()
                self.play = not self.play
                if not self.play:
                    # we zijn gestopt met spelen.
                    self.setcurrentticksandload(
                        self.roundtonoteticks(self.currentabsoluteticks)
                    )
                else:
                    # we zijn gestart met spelen
                    if (pygame.key.get_mods() & pygame.KMOD_SHIFT):
                        # als de shifttoets is ingedrukt, check of we kunnen loopen.
                        self.looping = False
                        if len(self.bookmarkticks) < 2:
                            if config.SMALLalerts:
                                self.setalert("Add more bookmarks to loop")
                            else:
                                self.setalert("Need another bookmark to start looping (shift+SPACE)")
                        else:
                            bookmarkindex = 0
                            self.loopingbookmarkindex = None
                            while bookmarkindex < len(self.bookmarkticks):
                                if self.bookmarkticks[bookmarkindex] == self.currentabsoluteticks:
                                    self.loopingbookmarkindex = bookmarkindex
                                    break
                                bookmarkindex += 1
                            if self.loopingbookmarkindex == None:
                                self.setalert("Not at a bookmark, can't loop here.")
                            else:
                                if self.loopingbookmarkindex < len(self.bookmarkticks) - 1:
                                    if self.bookmarkticks[self.loopingbookmarkindex + 1] > self.currentabsoluteticks:

                                        self.setalert("Looping from this bookmark to the next.")
                                        self.looping = True
                                    else:
                                        self.setalert("Next bookmark was placed behind this.")
                                else:
                                    self.setalert("At last bookmark, can't loop here.")

                return 1
            elif event.key == pygame.K_g:  # druk op de g toets
                self.currentnoteoffset = 0
                if (pygame.key.get_mods() & pygame.KMOD_SHIFT):
                    if len(self.piece.notes[self.currenttrack]):
                        lastmeasureticks = self.getlastmeasureticks()
                        if self.currentabsoluteticks != 0 and self.currentabsoluteticks != lastmeasureticks:
                            self.previousabsoluteticks = self.currentabsoluteticks
                        self.setcurrentticksandload(lastmeasureticks)
                        self.setalert("At end of piece.")
                    else:
                        if self.currentabsoluteticks != 0:
                            self.previousabsoluteticks = self.currentabsoluteticks
                        self.setcurrentticksandload(0)
                        self.setalert("No notes yet, going to beginning.")
                else:
                    if len(self.piece.notes[self.currenttrack]):
                        lastmeasureticks = self.getlastmeasureticks()
                        if self.currentabsoluteticks != 0 and self.currentabsoluteticks != lastmeasureticks:
                            self.previousabsoluteticks = self.currentabsoluteticks
                    else:
                        if self.currentabsoluteticks != 0:
                            self.previousabsoluteticks = self.currentabsoluteticks
                    self.setcurrentticksandload(0)
                    self.setalert("At beginning of piece.")
                self.play = False
                return 1
            elif event.key == pygame.K_j or event.key == pygame.K_DOWN:  # druk beneden
                if pygame.key.get_mods() & pygame.KMOD_CTRL:
                    return 0
                self.scoochbackward(pygame.key.get_mods() & pygame.KMOD_SHIFT)
                return 1
            elif event.key == pygame.K_k or event.key == pygame.K_UP:  # druk omhoog
                if pygame.key.get_mods() & pygame.KMOD_CTRL:
                    return 0
                self.scoochforward(pygame.key.get_mods() & pygame.KMOD_SHIFT)
                return 1
            elif event.key == pygame.K_PAGEUP:
                self.setcurrentticksandload(self.currentabsoluteticks +
                                            int((pygame.display.get_surface().get_height()) * (
                                                        1 - config.WHITEKEYfraction) / self.pixelspertick))
                self.setalert("Page up")
                return 1
            elif event.key == pygame.K_PAGEDOWN:
                self.setcurrentticksandload(max(0, self.currentabsoluteticks -
                                                int((pygame.display.get_surface().get_height()) * (
                                                            1 - config.WHITEKEYfraction) / self.pixelspertick)))
                self.setalert("Page down")
                return 1
            elif event.key == pygame.K_HOME:
                self.keymusic.centeredmidinote = config.LOWESTnote
                self.setalert("At lowest (piano) key")
                return 1
            elif event.key == pygame.K_END:
                self.keymusic.centeredmidinote = config.HIGHESTnote
                self.setalert("At highest (piano) key")
                return 1
            elif event.key == pygame.K_COMMA:  # druk komma
                self.tempomultiplier *= 100
                if (pygame.key.get_mods() & pygame.KMOD_SHIFT):
                    self.tempomultiplier -= 10
                else:
                    self.tempomultiplier -= 1

                if self.tempomultiplier < 10:
                    self.tempomultiplier = 10

                self.setalert("Speed to " + str(int(self.tempomultiplier)) + "%")
                self.tempomultiplier *= 1.0 / 100
                return 1
            elif event.key == pygame.K_PERIOD:  # druk punt
                self.tempomultiplier *= 100
                if (pygame.key.get_mods() & pygame.KMOD_SHIFT):
                    self.tempomultiplier += 10
                else:
                    self.tempomultiplier += 1

                if self.tempomultiplier > 300:
                    self.tempomultiplier = 300

                self.setalert("Speed to " + str(int(self.tempomultiplier)) + "%")
                self.tempomultiplier *= 1.0 / 100
                return 1
            elif event.key == pygame.K_c:
                # voeg een lied toe
                if (pygame.key.get_mods() & pygame.KMOD_SHIFT):
                    # als de shift is ingedrukt
                    if abs(self.keymusic.clicksounds[1].get_volume() / config.CLICKTRACKvolume - 1) < 0.1:
                        self.setalert("Upping clicktrack volume")
                        self.keymusic.clicksounds[0].set_volume(min(1, 10 * config.CLICKTRACKvolume * 1.1))
                        self.keymusic.clicksounds[1].set_volume(min(1, 10 * config.CLICKTRACKvolume))
                    else:
                        self.setalert("Lowering clicktrack volume")
                        self.keymusic.clicksounds[0].set_volume(min(1, config.CLICKTRACKvolume * 1.1))
                        self.keymusic.clicksounds[1].set_volume(min(1, config.CLICKTRACKvolume))

                    self.keymusic.metronome = True
                else:
                    self.keymusic.metronome = not self.keymusic.metronome
                    self.setalert("Click track " + ("on" if self.keymusic.metronome else "off"))
                return 1
            elif event.key == pygame.K_BACKQUOTE:
                if self.currentabsoluteticks != self.previousabsoluteticks:
                    lastmeasureticks = self.getlastmeasureticks()
                    initial = self.currentabsoluteticks
                    self.setcurrentticksandload(self.previousabsoluteticks)
                    if initial != 0 and initial != lastmeasureticks:
                        self.previousabsoluteticks = initial
                    self.setalert("Back to last jump point.")
                else:
                    self.setalert("At previous jump point.")

            elif event.key == pygame.K_b:
                if (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    try:
                        self.bookmarkticks.remove(self.currentabsoluteticks)
                        self.setalert("Bookmark removed.")
                    except ValueError:
                        self.bookmarkticks.append(self.currentabsoluteticks)
                        self.setalert("Bookmark added.  (Use b|B to visit others.)")

                elif len(self.bookmarkticks) == 0:
                    self.setalert("No bookmarks.  Add one with ctrl+b")

                elif len(self.bookmarkticks) == 1:
                    nextticks = self.bookmarkticks[0]
                    previous = self.currentabsoluteticks
                    if self.currentabsoluteticks != nextticks:
                        self.setcurrentticksandload(nextticks)
                        self.previousabsoluteticks = previous
                    if config.SMALLalerts:
                        self.setalert("At only bookmark.")
                    else:
                        self.setalert("At only bookmark.  Add more (or delete this one) with ctrl+b.")
                else:
                    if (pygame.key.get_mods() & pygame.KMOD_SHIFT):
                        # ga achteruit door de bladwijzers heen
                        nextticks = None
                        if self.currentabsoluteticks == self.bookmarkticks[0]:
                            nextticks = self.bookmarkticks[-1]
                            self.setalert("Looped back to last bookmark.")
                        else:
                            i = len(self.bookmarkticks) - 2
                            while i >= 0:
                                if self.currentabsoluteticks == self.bookmarkticks[i + 1]:
                                    nextticks = self.bookmarkticks[i]
                                    self.setalert("Back to bookmark " + str(i) + ".")
                                    break
                                i -= 1
                            if nextticks == None:
                                nextticks = self.bookmarkticks[-1]
                                self.setalert("At last bookmark.")

                        self.previousabsoluteticks = self.currentabsoluteticks
                        self.setcurrentticksandload(nextticks)

                    else:
                        # Ga vooruit door de bladwijzers
                        nextticks = None
                        if self.currentabsoluteticks == self.bookmarkticks[-1]:
                            nextticks = self.bookmarkticks[0]
                            self.setalert("Looped back to bookmark 0.")
                        else:
                            for i in range(len(self.bookmarkticks) - 1):
                                if self.currentabsoluteticks == self.bookmarkticks[i]:
                                    nextticks = self.bookmarkticks[i + 1]
                                    self.setalert("Advanced to bookmark " + str(i + 1) + ".")
                                    break
                            if nextticks == None:
                                nextticks = self.bookmarkticks[0]
                                self.setalert("At bookmark 0.")

                        self.previousabsoluteticks = self.currentabsoluteticks
                        self.setcurrentticksandload(nextticks)
                return 1

        return 0

    def commongrid(self, event, midi):
        # als we numerieke input hebben, verander de noot duur
        if event.key >= 48 and event.key < 58:  # nummers 1 (ascii 49) tot 9 (ascii 57)
            # nummer 1 = langste noot duur, 2 = korter, etc.
            self.currentnoteoffset = 0
            notecode = "b"
            if event.key == 48:  # 0
                notecode = "b/8"
            elif event.key <= 54:  # 1 tot 6
                notecode = "m/" + str(event.key - 48)
            else:
                # ascii 55 = 7, en 9 = ascii 57.
                notecode = "b/" + str(2 ** (event.key - 55))

            self.readnotecode(notecode)
            self.setcurrentticksandload(self.currentabsoluteticks, self.play)
            self.setalert("Note grid set to " + self.notecode)
            return 1
        elif event.key == 45:  #   HELP moeten we veranderen met 61
            if self.notebase == "m":
                # verminder nootduur van de nootbalk eenheid
                if self.notemultiplier > 1:
                    # schoon de notaties op:
                    if self.notedivider > 1:
                        notecode = str(self.notemultiplier - 1) + "m/" + str(self.notedivider)
                    else:
                        notecode = str(self.notemultiplier - 1) + "m"
                elif self.notedivider > 8:  # compleet willekeurig veranderen
                    notecode = "b"  # vanaf nu kwartnoten.
                else:
                    notecode = "m/" + str(self.notedivider + 1)
            else:
                # verminder nootduur van de nootbalk eenheid
                if self.notemultiplier > 1:
                    # schoon de notaties op:
                    if self.notedivider > 1:
                        notecode = str(self.notemultiplier - 1) + "b/" + str(self.notedivider)
                    else:
                        notecode = str(self.notemultiplier - 1) + "b"
                elif self.notedivider >= 15:
                    # dit is de kleinste eenheid
                    notecode = "b/16"
                else:
                    notecode = "b/" + str(self.notedivider + 1)

            self.readnotecode(notecode)
            self.setcurrentticksandload(self.currentabsoluteticks, self.play)
            self.setalert("Note grid set to " + self.notecode)
            return 1
        elif event.key == 61:  
            if self.notebase == "m":
                # verhoog noot duur van meetbalk eenheid
                if self.notedivider > 1:
                    if self.notemultiplier > 1:
                        notecode = str(self.notemultiplier) + "m/" + str(self.notedivider - 1)
                    else:
                        notecode = "m/" + str(self.notedivider - 1)
                elif self.notemultiplier >= 3:  # compleet willekeurig
                    notecode = "4m"  # ga niet over de noten die 4 noten lang of langer zijn
                else:
                    notecode = str(self.notemultiplier + 1) + "m"
            else:
                # verhoog noot duur van meetbalk eenheid
                if self.notedivider > 1:
                    if self.notemultiplier > 1:
                        notecode = str(self.notemultiplier) + "b/" + str(self.notedivider - 1)
                    else:
                        notecode = "b/" + str(self.notedivider - 1)
                elif self.notemultiplier >= 8:  # compleet willekeurig
                    notecode = "m"  # stap over naar metingen wannneer noten te groot worden.
                else:
                    notecode = str(self.notemultiplier + 1) + "b"
            self.readnotecode(notecode)
            self.setcurrentticksandload(self.currentabsoluteticks, self.play)
            self.setalert("Note grid set to " + self.notecode)
            return 1
        return 0

    def processmidi(self, midi):
        newnotes = midi.newnoteson()
        lastnote = -1
        for note in newnotes:
            midi.startnote(note[0], note[1],
                           self.piece.channels[self.currenttrack])  # start note[0] met velocity note[1]
            # verlicht ook de gebruikelijke toets op de achtergrond
            self.keymusic.brightenkey(note[0], note[1])
            lastnote = note[0]  # verkrijg alleen de midi noot, niet de snelheid

        newnotes = midi.newnotesoff()
        for note in newnotes:
            midi.endnote(note, self.piece.channels[self.currenttrack])  # stop noot

        return {}

    def draw(self, screen):
        # backdrop scherm
        self.backdrop.draw(screen)
        # teken keyboard en het muziek
        self.keymusic.draw(screen)
        if self.alerttext:
            self.alertbox.top = 10
            self.alertbox.right = screen.get_width() - 10

            screen.blit(self.alert, self.alertbox)

    def setalert(self, string, time=5000):
        self.alerttext = string
        self.alerttimer = time
        fontandsize = pygame.font.SysFont(config.FONT, int(21 * config.FONTSIZEmultiplier))
        self.alert = fontandsize.render(self.alerttext, 1, (255, 255, 255))
        self.alertbox = self.alert.get_rect()


# einde DDR class

class FlyingMusicElement(GameElementClass):
    def __init__(self, reltickpixels):
        self.reltickpixels = reltickpixels

    def draw(self, screen, topofkeys):
        pass

    def displace(self, displacement):
        self.reltickpixels -= displacement
        if self.reltickpixels < 0:
            return 1  # verwijder me
        else:
            return 0  # behoudt me


class MeasureBar(FlyingMusicElement):
    def __init__(self, reltickpixels, otherdivider=False):
        FlyingMusicElement.__init__(self, reltickpixels)
        if otherdivider:
            self.color = config.DIVIDERcolor
            self.linewidth = 1
        else:
            self.color = config.MEASUREcolor
            self.linewidth = 3

    def draw(self, screen, topofkeys):
        y = topofkeys - self.reltickpixels
        if y > 0:
            rightx = screen.get_width()
            pygame.draw.line(screen, self.color, (0, y), (rightx, y), self.linewidth)

    def displace(self, displacement):
        self.reltickpixels -= displacement
        if self.reltickpixels < -self.linewidth:
            return 1  # verwqijder me
        else:
            return 0


class FlyingText(FlyingMusicElement):
    def __init__(self, reltickpixels, text, fontsize=20):
        self.font = 'monospace'
        self.fontcolor = (250, 210, 250)
        self.fontsize = int(fontsize * config.FONTSIZEmultiplier)
        self.text = str(text)
        self.reltickpixels = reltickpixels
        self.fractionx = 0.4

        fontandsize = pygame.font.SysFont(self.font, self.fontsize)
        self.label = fontandsize.render(self.text, 1, self.fontcolor)
        self.labelbox = self.label.get_rect()

    def draw(self, screen, topofkeys):
        y = topofkeys - self.reltickpixels
        if y > 0:
            self.labelbox.bottom = y
            self.labelbox.right = (screen.get_width()) * self.fractionx
            screen.blit(self.label, self.labelbox)

    def displace(self, displacement):
        self.reltickpixels -= displacement
        if self.reltickpixels < -self.labelbox.height:
            # tempo verdwijnt nadat het beneden de toetsen samenvalt
            return 1  # verwijder me
        else:
            return 0


class FlyingTempo(FlyingText):
    def __init__(self, reltickpixels, bpm):
        FlyingText.__init__(self, reltickpixels, format("%.1f") % (bpm), 35)

    def draw(self, screen, topofkeys):
        # teken aan de linkerkant van het scherm
        y = topofkeys - self.reltickpixels
        if y > 0:
            self.labelbox.bottom = y
            self.labelbox.left = 10
            screen.blit(self.label, self.labelbox)


class FlyingTimeSignature(FlyingText):
    def __init__(self, reltickpixels, numerator):
        FlyingText.__init__(self, reltickpixels, str(int(numerator)), 40)

    def draw(self, screen, topofkeys):
        # teken aan de rechterkant van het scherm
        y = topofkeys - self.reltickpixels
        if y > 0:
            self.labelbox.bottom = y
            self.labelbox.right = screen.get_width() - 10
            screen.blit(self.label, self.labelbox)


class BottomPianoKeyClass(PianoKeyClass):
    ''' this class has methods for dealing with notes on/off '''

    def __init__(self, **kwargs):
        ''' this key is centered at x and anchored on the bottom by y '''
        PianoKeyClass.__init__(self, **kwargs)
        self.notes = deque([])
        self.notewidth = config.NOTEwidth

    def draw(self, screen, y):
        keypos = Rect(0, 0, self.width, self.length)
        keypos.centerx = self.x
        keypos.bottom = y

        if len(self.notes) > 0:
            screenheight = screen.get_height()  # y positie die aan de toets is gerelateerd
            lastnoteheight = screenheight
            if self.white:
                linercolor = (140, 140, 140)
            else:
                linercolor = (20, 20, 20)

            i = 0
            while i < len(self.notes):
                # teken de noot
                # note.draw( screen, self.x, pos.top, self.fillcoloron, linercolor )
                # def draw( self, screen, x, miny, fillcolor, outlinecolor ):
                notepos = Rect(0, 0, self.notewidth, screenheight)
                notepos.centerx = self.x
                try:
                    notepos.height = self.notes[i + 1][1] - self.notes[i][1]
                except IndexError:
                    pass
                notepos.bottom = keypos.top - self.notes[i][1]

                if notepos.bottom > 0:
                    # teken alleen als het onscreen is
                    noteoutline = Rect(notepos.left - 2, notepos.top - 2, notepos.width + 4, notepos.height + 4)
                    pygame.draw.rect(screen, linercolor, noteoutline)  # teken de buitenlijn
                    # teken kleur gebasseerd op kleur
                    notevelfrac = 1.0 * self.notes[i][0] / 128
                    grau = (1 - notevelfrac) * 120  # meer grijs als het een zachtgespeelde toon is
                    # hoe harder, hoe gekleurder:
                    notecolor = (int(notevelfrac * self.fillcoloron[0] + grau),
                                 int(notevelfrac * self.fillcoloron[1] + grau),
                                 int(notevelfrac * self.fillcoloron[2] + grau))
                    pygame.draw.rect(screen, notecolor, notepos)  # teken gevuld

                # check hoe laag het is
                if self.notes[i][1] < lastnoteheight:
                    lastnoteheight = self.notes[i][1]

                # verhoog met twee, omdat we ook met noten werkten die uitstonden in de "try"
                i += 2
            # teken een lijn die de laagste noot verbind met het keyboard
            if lastnoteheight > 0 and lastnoteheight < screenheight:
                linewidth = 2 + 200.0 / (lastnoteheight + 10)
                liner = Rect(0, 0, linewidth, lastnoteheight)
                liner.centerx = self.x
                liner.bottom = keypos.top
                pygame.draw.rect(screen, linercolor, liner)  # teken gevuld

        pygame.draw.rect(screen, self.fillcolor, keypos)  # teken gevuld

    def addnote(self, velocity, reltickspixels):
        ''' this note could be on (velocity>0) or off (velocity=0), with ticks
        relative to the top of the keyboard, but measured in pixels.'''
        if len(self.notes) > 0:
            self.notes.append([velocity, reltickspixels])
        else:
            if velocity:
                self.notes.append([velocity, reltickspixels])
            else:
                self.notes.append([100, 0])  # voeg een figuratieve noot toe
                self.notes.append([0, reltickspixels])  # en zet de off noot hier

    def clearallnotes(self):
        self.notes = deque([])

    def displacenotes(self, displacement):
        ''' displace all notes, HERE measured in pixels.'''
        if len(self.notes):
            if self.notes[0][0] == 0:  
                self.notes.appendleft([100, 0])

        i = 0
        while i < len(self.notes):
            # beweeg alle "on notes" omlaag
            if self.notes[i][1] > 0:
                self.notes[i][1] -= displacement  
            else:
                self.notes[i][1] = 0  

            try:
                # probeer alle "off notes" omlaag te bewegen.
                self.notes[i + 1][1] -= displacement
                if self.notes[i + 1][1] < 0:
                    # als de "off note" lager dan nul raakt, verwijder dan zowel de on als de off note
                    del self.notes[i]  # verwijder i en i+1
                    del self.notes[i]  # verwijder i en i+1
                else:
                    i += 2
            except IndexError:
                # dit gebeurt als we een on note hebben maar geen off note
                # we willen de on note houden en wachten op een andere off note.
                i += 1  # zodra we iets toevoegen zullen we uit de loop gaan


# dit was BOTTOMPIANO class.
class KeyboardAndMusicVisualsClass(GameElementClass):
    #### CLASS KEYBOARDANDMUSIC
    def __init__(self, **kwargs):
        self.allowedchanges = ["redmean", "redamp", "redfrequency", "redphase",
                               "greenmean", "greenamp", "greenfrequency", "greenphase",
                               "bluemean", "blueamp", "bluefrequency", "bluephase"]
        ## maak 88 toetsen
        self.keys = []
        # horizontale lijnen, zoals meetbalken, etc., maar ook tempo en tijdsnotatie verandering
        self.measures = []
        self.tempos = []
        self.timesignatures = []
        self.texts = []

        self.metronome = True
        self.clicksounds = [pygame.mixer.Sound(
            os.path.join("resources", "measureclick.ogg")
        ),
            pygame.mixer.Sound(
                os.path.join("resources", "barclick.ogg")
            )]
        self.clicksounds[0].set_volume(min(1, config.CLICKTRACKvolume * 1.1))
        self.clicksounds[1].set_volume(min(1, config.CLICKTRACKvolume))

        self.cursorpixels = 0  # hoever boven de piano zetten we de cursor
        self.selectanchor = 0  # waar de geselecteerde anker is, als het is gezet.  als gezet, [ midinote, relpixels ]
        self.cursorcolor = config.CURSORcolor  # cursor kleur

        self.defaulthalfwidth = config.KEYwidth / 2  # standaard halfbreedte van de witte toetsen
        self.k = 0.005  # veerconstante
        self.incrementnotedistance = []
        startingi = config.LOWESTnote  # laagste octaaf begint bij noot A
        self.effectivekeyhalfwidths = []
        endingi = 12  # alle octaven, op de hoogste na, lopen op tot 12
        for octaves in range(9):  # 9 octaven, maar de eerste en laatste zijn maar gedeeltelijk
            if octaves == 8:
                endingi = 1  # maar 1 toets in de laatste octaaf
            for i in range(startingi, endingi):
                ## maak the kleuren van de toetsen een regenboog
                if i in [0, 2, 4, 5, 7, 9, 11]:
                    # witte toetsen
                    self.effectivekeyhalfwidths.append(self.defaulthalfwidth)
                    self.keys.append(BottomPianoKeyClass(fillcoloroff=(200, 200, 200), length=130,
                                                         fillcoloron=config.rainbow[i], width=20))
                else:
                    # zwarte toetsen
                    self.effectivekeyhalfwidths.append(0)
                    self.keys.append(BottomPianoKeyClass(fillcoloroff=(20, 20, 20), length=80,
                                                         fillcoloron=config.rainbow[i], white=False,
                                                         width=15))

            startingi = 0  # de rest van de octaven begint met een C
        # laagste A heeft coëfficiënt 0, config.LOWESTnote
        # laagste C heeft coëfficiënt 3

        self.centeredmidinote = 60.0  # centreer het rondom de middelste C noot om mee te beginnen.

    #### CLASS KEYBOARDANDMUSIC
    def setstate(self, **kwargs):
        for key, value in kwargs.iteritems():
            if key in self.allowedchanges:
                setattr(self, key, value)
            else:
                Warn("in BottomPianoBackDropClass:setstate - key " + key + " is protected!!")

            #### CLASS KEYBOARDANDMUSIC

    def update(self, dt):
        for i in range(len(self.effectivekeyhalfwidths)):
            if self.effectivekeyhalfwidths[i] > 0:
                dx = self.effectivekeyhalfwidths[i] - self.defaulthalfwidth
                self.effectivekeyhalfwidths[i] -= self.k * dt * dx
        for key in self.keys:
            key.update(dt)

    #### CLASS KEYBOARDANDMUSIC
    def draw(self, screen):
        screenwidth, screenheight = screen.get_size()
        # hier tekenen we de metingen en al dat niet refereert aan de witte toets
        whitekeylength = config.WHITEKEYfraction * screenheight
        blackkeylength = config.BLACKKEYwhitefraction * whitekeylength

        keytop = screenheight - whitekeylength
        for meas in self.measures:
            meas.draw(screen, keytop)

        for text in self.texts:
            text.draw(screen, keytop)

        for tempo in self.tempos:
            tempo.draw(screen, keytop)

        for timesig in self.timesignatures:
            timesig.draw(screen, keytop)

        # het volgende dat we nodig hebben is alles dat we nodig hebben om de piano te tekenen. Pianos zijn ingewikkeld!
        #        whitekeylength = 0.13*screenheight # these were originally defined here.
        #        blackkeylength = 0.7*whitekeylength # now they are defined above!
        screencenterx = 0.5 * screenwidth

        blackkeyy = screenheight - (whitekeylength - blackkeylength)  # y positie van de zwarte toetsen
        # gemeten vanaf de onderkant.

        centerkeyindexNONINT = self.centeredmidinote - config.LOWESTnote  # maar dit is niet per se een integer
        centerkeyindex0 = int(centerkeyindexNONINT)
        eta = centerkeyindexNONINT - centerkeyindex0  # non-integer gedeelte van de centermidinote

        # zoek uit welke toets coëfficiënt je gaat centreren...
        if eta > 0.5:
            self.cursorkeyindex = centerkeyindex0 + 1
        else:
            self.cursorkeyindex = centerkeyindex0

        keyindexmin = centerkeyindex0  # dit opzoeken om te zien welke toetsen moeten worden getekend
        keyindexmax = centerkeyindex0  # dit opzoeken om te zien welke toetsen moeten worden getekend
        if (centerkeyindex0 < 0):  # centreer lager dan A
            Error(" Attempting to center the BottomBackGroundPiano on a note below low A!!")

        if (centerkeyindex0 > 87):  # centreer op de hoge C of hoger
            Error(" Attempting to center the BottomBackGroundPiano on a note higher than high C!!")
        # hier proberen we te centreren tussen centerkeyindex0 en centerkeyindex0+1

        self.keys[centerkeyindex0].x = screencenterx
        if eta:
            self.keys[centerkeyindex0].x -= eta * (self.effectivekeyhalfwidths[centerkeyindex0] +
                                                   self.effectivekeyhalfwidths[centerkeyindex0 + 1])

            # werk naar beneden om te zien welke toetsen zichtbaar zijn
        currentx = self.keys[centerkeyindex0].x - self.effectivekeyhalfwidths[centerkeyindex0]
        while keyindexmin > 0 and currentx > - self.effectivekeyhalfwidths[
            keyindexmin]:  # 0 is dee minimum toegestane toetscoëfficiënt
            keyindexmin -= 1  # maar als het 1 was, wordt dit 0.
            # het volgende gedeelte bevat wat problemen tussen witte en zwarte noten
            # witte noten bewegen via "currentx" maar zwarte noten niet
            halfwidth = self.effectivekeyhalfwidths[keyindexmin]
            currentx -= halfwidth
            self.keys[keyindexmin].x = currentx
            currentx -= halfwidth

        currentx = self.keys[centerkeyindex0].x + self.effectivekeyhalfwidths[centerkeyindex0]
        # werk omhoog om te zien welk noten zichtbaar zijn
        while keyindexmax < 87 and currentx < screenwidth + self.effectivekeyhalfwidths[keyindexmax]:
            # 87 is de max toegestane toets coëfficiënt
            keyindexmax += 1  # maar dit zal in werkelijkheid 87 zijn.
            # het volgende gedeelte bevat wat problemen tussen witte en zwarte noten
            # witte noten bewegen via "currentx" maar zwarte noten niet
            halfwidth = self.effectivekeyhalfwidths[keyindexmax]
            currentx += halfwidth
            self.keys[keyindexmax].x = currentx
            currentx += halfwidth
        try:
            # dit is nodig voor qwanner we een extra toets moeten tekenen
            # een zwarte toets.
            self.keys[keyindexmax + 1].x = screenwidth + 1000
        except IndexError:
            pass

        # begin nu het keyboard te tekenen
        if self.cursorpixels:
            if self.keys[self.cursorkeyindex].white:
                cursorrect = Rect(0, 0, 1.5 * self.effectivekeyhalfwidths[self.cursorkeyindex],
                                  self.cursorpixels)
            else:
                cursorrect = Rect(0, 0, 0.68 * (self.effectivekeyhalfwidths[self.cursorkeyindex - 1]
                                                + self.effectivekeyhalfwidths[self.cursorkeyindex + 1]),
                                  self.cursorpixels)
            cursorrect.centerx = self.keys[self.cursorkeyindex].x
            cursorrect.bottom = screenheight - whitekeylength
            # we teken de cursor nadat we het achtergrond hebben getekend.

            if self.selectanchor:
                # selectanchor heeft positie [ midinote, farthest-reach-in-rexels ]
                if self.selectanchor[0] > 127 or self.selectanchor[0] < 0:
                    # als we zeggen om midi note 128 ( of -1) te selecteren, bedoelen we selecteer allemaal
                    if self.selectanchor[1] >= self.cursorpixels:
                        # het cijfer is hoger dan de huidige cursor rexels
                        selectorrect = Rect(0, 0, screenwidth, self.selectanchor[1] + self.cursorpixels)
                    else:
                        selectorrect = Rect(0, 0, screenwidth, self.cursorpixels)

                else:
                    selindex = self.selectanchor[0] - config.LOWESTnote

                    if self.keys[selindex].white:
                        selectorrect = Rect(0, 0, 1.5 * self.effectivekeyhalfwidths[selindex],
                                            self.cursorpixels)
                    else:
                        selectorrect = Rect(0, 0, 0.68 * (self.effectivekeyhalfwidths[selindex - 1]
                                                          + self.effectivekeyhalfwidths[selindex + 1]),
                                            self.cursorpixels)
                    # vind nu de placering uit. Kijk wat de linker/recther kant van dingen zijn.
                    selectorrect.centerx = self.keys[selindex].x
                    # vind nu de hoogte uit.
                    if self.selectanchor[1] >= self.cursorpixels:
                        # het cijfer is hoger dan het huidige cursor rexels
                        selectorrect.top = cursorrect.top - self.selectanchor[1]
                    else:
                        selectorrect.bottom = cursorrect.bottom

                    selectorrect.union_ip(cursorrect)

                selectorrect.bottom = cursorrect.bottom
                pygame.draw.rect(screen, (0.5 * self.cursorcolor[0],
                                          0.5 * self.cursorcolor[1],
                                          0.5 * self.cursorcolor[2]), selectorrect)

            pygame.draw.rect(screen, self.cursorcolor, cursorrect)

        #  begin beneden en teken ze allemaal
        keyindex = keyindexmin
        while keyindex <= keyindexmax:
            if self.keys[keyindex].white:
                self.keys[keyindex].setstate(length=whitekeylength,
                                             width=1.5 * self.effectivekeyhalfwidths[keyindex])
                self.keys[keyindex].draw(screen, screenheight)
                keyindex += 1
            else:  # zwarte toets
                # teken eerst de witte toets erboven
                self.keys[keyindex + 1].setstate(length=whitekeylength,
                                                 width=1.5 * self.effectivekeyhalfwidths[keyindex + 1])
                self.keys[keyindex + 1].draw(screen, screenheight)
                # teken dan de zwarte toets
                self.keys[keyindex].setstate(length=blackkeylength,
                                             width=0.68 * (self.effectivekeyhalfwidths[keyindex + 1] +
                                                           self.effectivekeyhalfwidths[keyindex - 1]))
                self.keys[keyindex].draw(screen, blackkeyy)
                # VERHOOG NU MET TWEE
                keyindex += 2

    #### CLASS KEYBOARDANDMUSIC
    def addnote(self, midinote, velocity, startlocation):
        ''' a note has a beginning and a duration, measured in ticks.
        startlocation is PIXELS relative to the keyboard
        (0 = just above keyboard, time to get hit by player)'''
        #        self.resolution = 100 # ticks per beat, bepaald door de piece
        #        self.pixelsperbeat = 200 # gegeven als een config
        #        self.pixelspertick = 1.0 * self.pixelsperbeat / self.resolution # pixels/beat / (ticks/beat)

        keyindex = (midinote - config.LOWESTnote)
        if keyindex >= 0 and keyindex <= 87:
            # als jje probeert een "off note" toe te voegen voordat we on notes hebben...
            #            if velocity == 0 en len(self.keys[keyindex].notes) == 0:
            #                # voeg dan een "on" toe bij het begin...
            #                self.keys[ keyindex ].addnote( 100, 0 )
            #            # voeg de off later toe.  of voeg de on note toe als het een on note is
            self.keys[keyindex].addnote(velocity, startlocation)

    #        for note in self.keys[ keyindex ].notes:
    #            print " midi ", midinote, ":  note0 = ",note[0], "; note1 = ",note[1]

    def clearallmusic(self):
        for key in self.keys:
            key.clearallnotes()

        # verwijder alle vliegende balken
        self.measures = []
        self.tempos = []
        self.timesignatures = []
        self.texts = []

    def addmeasurebar(self, reltickpixels, otherdivider=False):
        self.measures.append(MeasureBar(reltickpixels, otherdivider))

    def addtempo(self, reltickpixels, bpm):
        self.tempos.append(FlyingTempo(reltickpixels, bpm))

    def addtimesignature(self, reltickpixels, numerator):
        self.timesignatures.append(FlyingTimeSignature(reltickpixels, numerator))

    def addtext(self, reltickpixels, text):
        self.texts.append(FlyingText(reltickpixels, text))
        if len(self.texts) > 1:
            if abs(self.texts[-1].reltickpixels - self.texts[-2].reltickpixels) < 10:
                self.texts[-1].fractionx = 0.3
                self.texts[-2].fractionx = 0.7

    def clearmeasurebarsafter(self, reltickpixels):
        i = len(self.measures) - 1
        while i >= 0:
            if self.measures[i].reltickpixels >= reltickpixels:
                del self.measures[i]
            i -= 1

    def displaceallmusic(self, displacement):
        ''' displace all notes by some amount in pixels.  positive displacement moves everything down. '''
        for key in self.keys:
            key.displacenotes(displacement)

        # doe metingen
        i = 0
        while i < len(self.measures):
            if self.measures[i].displace(displacement):
                # als de vliegende muziekale elementem ons seint om het verwijderen.
                # als het nodig is, speel eerst metronoom af
                if self.metronome:
                    if self.measures[i].linewidth > 1:
                        self.clicksounds[0].play()
                    else:
                        self.clicksounds[1].play()

                # en verwijder het dan
                del self.measures[i]
            else:
                # anders, verhoog en ga door
                i += 1

        # bepaal tempo's
        i = 0
        while i < len(self.tempos):
            if self.tempos[i].displace(displacement):
                # als de muziekale elementen ons sienen om te verwijderen
                # verwijder het
                del self.tempos[i]
            else:
                # anders, verhoog en ga door
                i += 1

        # maak dan tijdsnotaties
        i = 0
        while i < len(self.timesignatures):
            if self.timesignatures[i].displace(displacement):
                # als de muziekale elementen ons sienen om te verwijderen
                # verwijder het
                del self.timesignatures[i]
            else:
                # anders, verhoog en ga door
                i += 1

        # maak teksten
        i = 0
        while i < len(self.texts):
            if self.texts[i].displace(displacement):
                # als de muziekale elementen ons sienen om te verwijderen
                # verwijder het
                del self.texts[i]
            else:
                # anders, verhoog en ga door
                i += 1

    #### CLASS KEYBOARDANDMUSIC
    def hitrandomkey(self, midi, midioctave=5, notevel=100):  # midioctave = 5 is de midddelste C
        randompiano = int(random() * 12)
        self.setstate(redphase=randomphase(),
                      greenphase=randomphase(),
                      bluephase=randomphase())
        ## en speel het in midi:
        self.hitkey(midi, randompiano + midioctave * 12, notevel)

    #### CLASS KEYBOARDANDMUSIC
    def brightenkey(self, midinote=60, notevel=100):  # midinote = 60 is middelste C
        # zet de toets flits aan
        keyindex = (midinote - config.LOWESTnote)
        if keyindex >= 0 and keyindex <= 87:
            self.keys[keyindex].setstate(on=notevel)
            self.centeredmidinote += 0.01 * (midinote - self.centeredmidinote)
            if self.effectivekeyhalfwidths[keyindex] > 0:
                self.effectivekeyhalfwidths[keyindex] += 2
            else:
                try:
                    self.effectivekeyhalfwidths[keyindex + 1] += 1
                    self.effectivekeyhalfwidths[keyindex - 1] += 1
                except IndexError:
                    pass
            ## en speel het in midi:
        else:
            Warn(" Attempted to play strange note " + str(midinote) + " in BottomPiano... ")

    #### CLASS KEYBOARDANDMUSIC
    def hitkey(self, midi, midinote=60, notevel=100,
               duration=1, channel=0, playsound=True):  # midinote = 60 is middelste C
        # zet de toets flits aan
        self.brightenkey(midinote, notevel)
        if playsound:
            midi.playnote(midinote, notevel, duration, channel)

    def scoochkeyboard(self, leftright):
        self.centeredmidinote += leftright
        if self.centeredmidinote < config.LOWESTnote:
            self.centeredmidinote = config.LOWESTnote
        elif self.centeredmidinote > config.HIGHESTnote:
            self.centeredmidinote = config.HIGHESTnote

    def setcursorheight(self, pixels=0):
        self.cursorpixels = pixels

    def setselectanchor(self, pixels=0):
        # als het nul is, zien we niets
        # anders, gebruik je [ midinote, rexel ]
        # waar rexel de pixel afstand vanaf de onderkant is.
        self.selectanchor = pixels

#### EIND CLASS KEYBOARDANDMUSIC
