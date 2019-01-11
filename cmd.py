import pygame
import config
from collections import deque # voor het snel poppen van lists zodat je niet lang hoeft te wachten
import itertools

class CommandClass( object ): 
#### COMMAND CLASS
    def __init__( self, commandactivate, commandname="cmd" ):
        self.commandfont = config.FONT
        self.commandfontcolor = (255,255,255)
        self.commandfontsize = int(24*config.FONTSIZEmultiplier)
        self.commandbackcolor = (0, 0, 0)
        
        self.commandname = commandname
        self.commandhistory = deque([], config.COMMANDhistory)
        self.commandindex = -1
        # for grabbing information...
        self.commanddo = commandactivate
        self.command = ""
    
    def process( self, event, midi ):
        if event.type == pygame.KEYDOWN:
            # wachten voor input
            if event.key == 27:
                if self.commandindex < 0:
                    if len(self.command):
                        if len(self.commandhistory):
                            if self.commandhistory[0] != self.command:
                                self.commandhistory.appendleft(self.command)
                        else:
                            self.commandhistory.appendleft(self.command)
                else:
                    # wijzig wat je hebt geschreven in de commandline:
                    if (  self.command != self.commandhistory[self.commandindex]
                    and ( self.commandindex == 0 
                      or self.command != self.commandhistory[self.commandindex-1] )  ):
                        self.commandhistory = deque( 
                            list(itertools.islice(self.commandhistory,0,self.commandindex))+
                            [self.command] +
                            list(itertools.islice(self.commandhistory,self.commandindex,len(self.commandhistory))),
                            config.COMMANDhistory )
                    
                self.commandindex = -1
                self.command = ""
                return self.commanddo( "", midi )
                
            elif event.key == pygame.K_BACKSPACE:
                self.command = self.command[0:-1] # Verwijder laatste ingevoerde letter.

            elif event.key == pygame.K_RETURN:
                if self.command:
                    # voeg toe in history:
                    if not len(self.commandhistory) or self.commandhistory[0] != self.command:
                        self.commandhistory.appendleft( self.command )
                    # laat het staan
                    thecommand = self.command
                    # verwijder het voor de volgende keer
                    self.command = ""
                    # gebruik het in de history.
                    return self.commanddo( thecommand, midi ) 
                else:
                    return self.commanddo( "", midi ) 

            elif event.key == pygame.K_UP:
                # navigeer door je command history
                if self.commandindex < 0:
                    if len(self.command):
                        if len(self.commandhistory):
                            if self.commandhistory[0] != self.command:
                                self.commandhistory.appendleft(self.command)
                                self.commandindex = 0
                        else:
                            self.commandhistory.appendleft(self.command)
                            self.commandindex = 0
                else:
                    if (  self.command != self.commandhistory[self.commandindex]
                    and ( self.commandindex == len(self.commandhistory)-1 
                      or self.command != self.commandhistory[self.commandindex+1] )   ):
                        self.commandhistory = deque( 
                            list(itertools.islice(self.commandhistory,0,self.commandindex+1))+
                            [self.command] +
                            list(itertools.islice(self.commandhistory,self.commandindex+1,len(self.commandhistory))),
                            config.COMMANDhistory 
                        )
                        self.commandindex += 1
                    
                self.commandindex += 1
                if self.commandindex >= len(self.commandhistory):
                    self.commandindex = len(self.commandhistory)-1
                self.command = self.commandhistory[ self.commandindex ]
            
            elif event.key == pygame.K_DOWN:
                # navigeer door je history
                if self.commandindex < 0:
                    if len(self.command):
                        if len(self.commandhistory):
                            if self.commandhistory[0] != self.command:
                                self.commandhistory.appendleft(self.command)
                        else:
                            self.commandhistory.appendleft(self.command)
                else:
                    # als we in de command history zitten kijk of je er ook echt in zit.
                    # wijzig wat je hebt geschreven in de commandline:
                    if (  self.command != self.commandhistory[self.commandindex]
                    and ( self.commandindex == 0 
                      or self.command != self.commandhistory[self.commandindex-1] )  ):
                        self.commandhistory = deque( 
                            list(itertools.islice(self.commandhistory,0,self.commandindex))+
                            [self.command] +
                            list(itertools.islice(self.commandhistory,self.commandindex,len(self.commandhistory))),
                            config.COMMANDhistory )
                        #self.commandindex -= 1
                    
                self.commandindex -= 1
                if self.commandindex < 0:
                    self.command = ""
                else:
                    self.command = self.commandhistory[ self.commandindex ]

            elif event.key == pygame.K_PAGEUP:
                # navigeer door je History
                if self.commandindex < 0:
                    if len(self.command):
                        if len(self.commandhistory):
                            if self.commandhistory[0] != self.command:
                                self.commandhistory.appendleft(self.command)
                                self.commandindex = 0
                        else:
                            self.commandhistory.appendleft(self.command)
                            self.commandindex = 0
                else:
                    # als we in de command history zitten kijk of je er ook echt in zit.
                    # wijzig wat je hebt geschreven in de commandline:
                    if (  self.command != self.commandhistory[self.commandindex]
                    and ( self.commandindex == len(self.commandhistory)-1 
                      or self.command != self.commandhistory[self.commandindex+1] )  ):
                        self.commandhistory = deque( 
                            list(itertools.islice(self.commandhistory,0,self.commandindex+1))+
                            [self.command] +
                            list(itertools.islice(self.commandhistory,self.commandindex+1,len(self.commandhistory))),
                            config.COMMANDhistory 
                        )
                        
                        self.commandindex += 1
                
                if len(self.commandhistory): 
                    self.commandindex = len(self.commandhistory)-1
                    self.command = self.commandhistory[ self.commandindex ]
                else:
                    self.commandindex = -1
                    self.command = ""
            
            elif event.key == pygame.K_PAGEDOWN:
                # navigeer door je History
                if self.commandindex < 0:
                    if len(self.command):
                        if len(self.commandhistory):
                            if self.commandhistory[0] != self.command:
                                self.commandhistory.appendleft(self.command)
                        else:
                            self.commandhistory.appendleft(self.command)
                else:
                    # als we in de command history zitten kijk of je er ook echt in zit.
                    # wijzig wat je hebt geschreven in de commandline:
                    if (  self.command != self.commandhistory[self.commandindex]
                    and ( self.commandindex == 0 
                      or self.command != self.commandhistory[self.commandindex-1] )  ):
                        self.commandhistory = deque( 
                            list(itertools.islice(self.commandhistory,0,self.commandindex))+
                            [self.command] +
                            list(itertools.islice(self.commandhistory,self.commandindex,len(self.commandhistory))),
                            config.COMMANDhistory )
                    
                self.commandindex = -1
                self.command = ""

            elif event.key < 128:
                newletter = chr(event.key) #dit is de nieuwe letter
                if pygame.key.get_mods() & pygame.KMOD_SHIFT: #als de shift key ingedrukt is
                    newletter = newletter.upper() # maak er een hoofdletter van
                self.command += newletter # voeg toe aan het bericht
        
        return {}

#### COMMAND CLASS 

    def draw( self, screen ):
        fontandsize = pygame.font.SysFont(self.commandfont, self.commandfontsize)
        commanddrawtext = fontandsize.render( self.commandname + ": " + self.command, 
                                            1, self.commandfontcolor )
        commanddrawbox = commanddrawtext.get_rect()
        commanddrawbox.left = 10
        commanddrawbox.bottom = screen.get_height() - 10
        pygame.draw.rect( screen, self.commandbackcolor, commanddrawbox )
        screen.blit( commanddrawtext, commanddrawbox )

#### END COMMAND CLASS
