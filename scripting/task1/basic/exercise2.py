#!/usr/bin/env python3

def use_dummy():
   dummy = 0
   for ii in range(1,11):
       print(f"{dummy} + {ii} = {dummy + ii}")
       dummy = ii


def use_consecutive():
    for ii in range(1,11):
        print(f"{ii-1} + {ii} = {2*ii-1}")


def fibonacci():
    prev = 0
    old = 0
    new = 1
    for __ in range(1,11):
        old = new
        new = prev + old
        print(f"{prev} + {old} = {new}")
        prev = old


if (__name__ == "__main__"):

    print("Dummy variable:")
    use_dummy()
    print()
    
    print("Consecutive numbers: n + (n-1) = 2n-1")
    use_consecutive()
    print()
    
    print("Fibonacci sequence:")
    fibonacci()
