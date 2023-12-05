#!/usr/bin/env python3
"""
Create your Heroes and have them battle
(in memory of Ultimate Showdown of Ultimate Destiny)
"""

import sys

# welcome message
def welcome():
    print()
    print("| Ultimate Showdown of Ultimate Destiny |")
    print()


# heroes
class Hero:

    # hero class knows how heroes are created
    @classmethod
    def read_hero(cls):
        print("| Create your hero |")
        print("Format: Type Name ATK DEF")
        
        for line in sys.stdin:
            input_list = line.strip().split()
            # transform ATK, DEF stats to integers
            input_list[2:4] = [ int(entry) for entry in input_list[2:4] ]
            if (len(input_list)!=4):
                print("Your hero is incomplete!")
            else:
                break

        return input_list


    def __init__(self,htype,name,attack,defense):
        self.htype = htype
        self.name = name
        # ATK in range [0:100]
        self.attack_strength = attack
        # DEF range [0:100]
        self.defense_strength = defense


    def attack(self):
        return self.attack_strength


    def defense(self):
        return self.defense_strength


    def clash(self,opponent):
        print(f"{self.name} and {opponent.name} clash")
        print()

        #clash
        opponent.defense_strength -= self.attack()
        self.defense_strength -= opponent.attack()

        # compare defense values
        if (self.defense() > opponent.defense()):
            print(f"{self.name} wins")
        elif (self.defense() < opponent.defense()):
            print(f"{opponent.name} wins")
        else:
            print(f"It's a draw")

        # TODO: add initiative, add turn based combat,
        # add TKO, replace defense_strength with HP, 
        # add tournament mode, add prepared heroes 
        # (see Appendix)

    def write_hero():
        pass
        # TODO save heroes in files


if (__name__ == "__main__"):

    # welcome message
    welcome()
    
    # user creates heroes
    h1 = Hero.read_hero()
    hero1 = Hero(*h1)
    h2 = Hero.read_hero()
    hero2 = Hero(*h2)
    
    # heroes clash
    hero1.clash(hero2)

# raven = Hero("DC","Raven",70,30)
# terra = Hero("DC","Terra",50,65)
# silver_surfer = Hero("Marvel","Silver Surfer",80,40)
# hawkeye = Hero("Marvel","Hawkeye",90,20)

# raven.clash(terra)
# terra.clash(raven)
# silver_surfer.clash(hawkeye)


# Appendix

# List of DC heroes:
# Superman
# Batman
# Wonder Woman
# Green Lantern
# The Flash
# Aquaman
# Cyborg
# Batgirl
# Batwoman
# Beast Boy
# Blue Beetle
# Green Arrow
# Nightwing
# Raven
# Robin
# Shazam
# Starfire
# Terra

# List of Marvel heroes:
# Ant-Man
# Black Panther
# Black Widow
# Captain America
# Daredevil
# Deadpool
# Ghost Rider
# Groot
# Hawkeye
# Hellion
# Hulk
# Iron Man
# Magneto
# Punisher
# Silver Surfer
# Spider-Man
# Thor


