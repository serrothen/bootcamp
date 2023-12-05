#!/usr/bin/env python3

import re

word1 = "redivider"
word2 = "onomatopoeia"
sentence = "Mr. Owl ate my metal worm"


def palindrome(word):
    result = False

    # compare first half of word with mirrored second half of word
    len_half = len(word)//2
    if ( word[:len_half] == word[-len_half:][::-1] ):
        result = True

    return result


if (__name__ == "__main__"):

    if ( palindrome(word1) ):
        print(f"'{word1}' is a palindrome")
    else:
        print(f"'{word1}' is not a palindrome")
    print()
    
    if ( palindrome(word2) ):
        print(f"'{word2}' is a palindrome")
    else:
        print(f"'{word2}' is not a palindrome")
    print()
    
    # remove whitespace and period, convert to lower case
    sentence_mod = re.sub('[\s\.]','',sentence).lower()
    if ( palindrome(word1) ):
        print(f"'{sentence}' is a palindrome")
    else:
        print(f"'{sentence}' is not a palindrome")
