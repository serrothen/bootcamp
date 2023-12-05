#!/usr/bin/env python3

""" Editing module """

import sys
from rich.table import Table
from rich.console import Console


# output content
def output_table(content):
    table = Table()
    console = Console()
    
    table.add_column("Name")
    table.add_column("Age")
    table.add_column("Grade")
    
    for entry in content:
        table.add_row(*entry)
    
    console.print(table)


# welcome message
def welcome():
    print()
    print("| Store your students (TM) |")
    print("| Editing module |")
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


# read data from file
def read_data(fname):
    content = []
    with open(fname,"r") as storage:
        for line in storage:
            content.append(line.strip().split())

    # display data
    print("Data base:")
    output_table(content)

    return content


# add student to data base
def add_student(content):
    print("| Enter student data |")
    print("Format: 'Name Age Grade'")

    input_clean = sys.stdin.readline().strip()

    if (input_clean != ""):
        content.append(input_clean.split())

    # TODO: check if format correct

    return content


# remove student from data base
def remove_student(content):
    # convert data to dictionary: simpler editing
    content_dict = {entry[0]: entry[1:] for entry in content}

    print("Enter student Name")
    for line in sys.stdin:

        input_clean = line.strip()

        if (input_clean in content_dict.keys()):
            content_dict.pop(input_clean)
            # convert dictionary to list (list val needs unpacking)
            content_mod = [[key,*val] for key,val in content_dict.items()]
            break
        elif (input_clean == "quit"):
            content_mod = content
            break
        else:
            print(f"No student with Name {input_clean}. Try again or enter 'quit'")

    # TODO: check if format correct

    return content_mod


# modify student in data base
def edit_student(content):
    # convert data to dictionary: simpler editing
    content_dict = {entry[0]: entry[1:] for entry in content}

    print("Enter student Name")
    for line0 in sys.stdin:

        # read name
        input_clean = line0.strip()

        # edit entries
        if (input_clean in content_dict.keys()):
            print(f"Name {input_clean}: {content_dict[input_clean]}")
            print(f"Enter edited entries")

            for line1 in sys.stdin:
                input_edit = line1.strip().split()
                if (len(input_edit) == 2):
                    content_dict[input_clean] = input_edit
                    content_mod = [[key,*val] for key,val in content_dict.items()]
                    break
                elif (input_edit[0] == "quit"):
                    content_mod = content
                    break
                else:
                    print(f"Invalid entries. Try again or enter 'quit'")

            break
        elif (input_clean == "quit"):
            content_mod = content
            break
        else:
            print(f"No student with Name {input_clean}. Try again or enter 'quit'")

    # TODO: check if format correct

    return content_mod


# write data to file
def write_data(content,fname):
    # write to file
    with open(fname,"w") as storage:
        for entry in content:
            storage.write(" ".join(entry)+"\n")


# menu of user options to edit data base
def menu(content,fname):

    for line in sys.stdin:
        print("| Options to edit data base |")
        print("add: Add student to data base")
        print("remove: Remove student from data base")
        print("edit: Edit student data")
        print("write: Write modified data base to file")
        print("quit: Quit without writing data to file")
        print()

        input_clean = sys.stdin.readline().strip()

        if (input_clean == "add"):
            print("| Adding student to data base |")
            content = add_student(content)
            output_table(content)
            print()
        elif (input_clean == "remove"):
            print("| Removing student from data base |")    
            content = remove_student(content)
            output_table(content)
            print()
        elif (input_clean == "edit"):
            print("| Edit student data |")
            content = edit_student(content)
            output_table(content)
            print()
        elif (input_clean == "write"):
            print("| Writing data to file |")
            write_data(content,fname)
            print()
        elif (input_clean == "quit"):
            print("| Quit without writing data to file |")
            break
        else:
            print("Invalid option")


if __name__ == "__main__":
    # interface
    welcome()
    
    # get filename
    fname = get_fname()
    
    # read data from file
    content = read_data(fname)
    
    # menu of user options to edit data base
    menu(content,fname)
