#!/usr/bin/env python3
""" Storage module """


import sys
from rich.table import Table
from rich.console import Console


# output content
def output_table(content):
    # setup
    table = Table()
    console = Console()
    # columns
    table.add_column("Name")
    table.add_column("Age")
    table.add_column("Grade")
    # add rows
    for entry in content:
        table.add_row(*entry)
    # output
    console.print(table)


# welcome message
def welcome():
    print()
    print("| Store your students (TM) |")
    print("| Storage module |")
    print()


# get filename
def get_fname():
    fname = "students.txt"
    print("Filename (press enter to use default)")
    input_clean = sys.stdin.readline().strip()
    if (input_clean != ""):
        fname = input_clean
    print()

    return fname


# read data from stdin
def read_init():
    print("| Enter student data |")
    print("Format: 'Names Age Grade'")
    print("To quit, enter an empty line")
    print()

    content = []
    for line in sys.stdin:
        input_clean = line.strip()
        # quit
        if (input_clean == ""):
            break
        content.append(input_clean.split())

        # TODO: check if format correct

        # update displayed data
        output_table(content)

    return content


# write data to file
def write_data(content,fname):
    # file exists: append to file
    # file does not exist: create new file
    with open(fname,"a") as storage:
        for entry in content:
            storage.write(" ".join(entry)+"\n")


if (__name__ == "__main__"):

    # interface
    welcome()
    
    # get filename
    fname = get_fname()
    
    # read data from stdin
    content = read_init()
    
    # write data to file
    write_data(content,fname)


