#!/usr/bin/env python3

if (__name__ == "__main__"):

    s_old = "In Flanders fields the poppies blow Between the crosses, row on row,"
    pos = 7
    
    # cannot change string in-place: string immutable 
    print("Slicing:")
    s_new = s_old[pos:]
    print(s_old)
    print( pos*"." + s_new )
