#!/usr/bin/env python3

import random

def filter_loop(lst):
    for entry in lst:
        if (entry%5==0):
            print(entry)

def filter_comprehension(lst):
    lst_div = [entry for entry in lst if entry%5==0]
    for entry in lst_div:
        print(entry)


if (__name__ == "__main__"):

    # number of elements
    num_list = 20
    
    # consecutive numbers
    lst1 = [ii for ii in range(num_list)]
    
    # random numbers
    start = -10
    stop = 25
    lst2 = [random.randint(start,stop) for __ in range(num_list)]
    
    
    print("Filter inside loop:")
    print("List 1:")
    filter_loop(lst1)
    print("List 2:")
    filter_loop(lst2)
    print()
    
    
    print("List comprehension:")
    
    print("List 1:")
    filter_comprehension(lst1)
    print("List 2:")
    filter_comprehension(lst2)
