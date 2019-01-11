# Dit is de __main__ python code.  run "python pikey.py" om het openen(In dezelfde directory).
from game import *

# define main function
def main():
    game = GameClass()
    game.mainloop()

# Run dit als execute en niet als module want dan gebeurt er niks.
if __name__=="__main__":
    # roept de main functie aan.
    main()

