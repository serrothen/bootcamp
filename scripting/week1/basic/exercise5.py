#!/usr/bin/env python3
"""
Count substring in string
"""
import re

def str_count(text,substring):
    return text.count(substring)

def regex(text,substring):
    return len(re.findall(substring,text))

def sliding_window(text,substring):
    # move substring over text and check overlay
    len_text = len(text)
    len_sub = len(substring)
    num_sub = 0
    # prevent index out of bounds
    for ii in range(len_text-len_sub):
        if (substring == text[ii:ii+len_sub]):
            num_sub += 1
    return num_sub



text = """
In Flanders fields
by John McCrae

 In Flanders fields the poppies blow
Between the crosses, row on row,
    That mark our place; and in the sky
    The larks, still bravely singing, fly
Scarce heard amid the guns below.

We are the Dead. Short days ago
We lived, felt dawn, saw sunset glow,
    Loved and were loved, and now we lie,
        In Flanders fields.

Take up our quarrel with the foe:
To you from failing hands we throw
    The torch; be yours to hold it high.
    If ye break faith with us who die
We shall not sleep, though poppies grow
        In Flanders fields.
"""


if (__name__ == "__main__"):

    print(f"Text: '{text}'")
    substring = input("Which substring shall be counted? ").strip()
    
    
    print('str.count:')
    num_sub = str_count(text,substring)
    print(num_sub)
    print()
    
    print('Regex:')
    num_sub = regex(text,substring)
    print(num_sub)
    print()
    
    print('Sliding window:')
    num_sub = sliding_window(text,substring)
    print(num_sub)

