#!/usr/bin/env python3
"""
checkLogins: Check ssh logins.
Create-mode:
    *Creates database, creates and fills relations.
    *Runs a set of SQL-queries to check the database.
Append-mode:
    Add new entries to the datbase without having to
    recreate it again.
Interactive-mode:
    Processes queries on created database.
User-mode:
    Display data through a simple CLI.
Setup-mode: (Experimental)
    Setup a cronjob to run the script in
    Append-mode regularly.

Classes:

    LogFile
    CronJob
    Relation
    Database
    SQLUser
    User
"""

# Python Standard Library
import re
import subprocess
import sys
from getpass import getpass
import csv
import itertools
import textwrap
from functools import wraps
import readline
from datetime import datetime,timedelta
import os

# Third-party libraries
import psycopg2
from psycopg2 import sql
import rich
from rich.table import Table
from rich.console import Console


class LogFile:
    """
    A class to represent a Log file.

    ...

    Attributes
    ----------
    _name : str
        name of the Log file
    _location : str
        path to the Log file

    Methods
    -------
    copy_log(destination):
        Copies Log to destination.
    rm_log():
        Removes Log file.
    _read_log():
        Reads from Log file, one line at a time.
    message_filter(logged_sessions,pid,message,user_list):
        Filter a message for attributes.
    process_log(user_list,buffer_time,break_time):
        Examines Log and extracts relevant data.
    """

    def __init__(self,name,location):
        """Constructs necessary attributes of the LogFile object."""

        self._name = name
        self._location = location


    def copy_log(self,destination):
        """
        Copies Log to destination.
    
           Parameters:
               destination (str): Absolute path
        """

        cmd = f"cp {self._location}/{self._name} {destination}"
        subprocess.call(cmd,shell=True)
        self._location = destination


    def rm_log(self):
        """Removes Log file."""

        cmd = f"rm {self._location}/{self._name}"
        subprocess.call(cmd,shell=True)


    def _read_log(self):
        """Reads from Log file, one line at a time."""

        fname = f"{self._location}/{self._name}"
        try:
            with open(fname,"r") as logfile:
                for line in logfile:
                    yield line
        except FileNotFoundError:
            msg = f"The file {fname} does not exist."
            print(msg)
        except PermissionError:
            msg = f"You lack permission to read {fname}."
            print(msg)

    @staticmethod
    def message_filter(logged_sessions,pid,message,user_list):
        """Filter a message for attributes."""

        # IP address
        pattern = r"("+r"[0-9]{1,3}\."*3+r"[0-9]{1,3})"
        search = re.search(pattern,message)
        if (bool(search)):
            logged_sessions[pid]["ip_address"] = search.group(1)

        # username, user existence
        pattern = r"(password for |user |user=)(?!invalid|unknown)(\w+)"
        search = re.search(pattern,message)
        if (bool(search)):
            logged_sessions[pid]["user_name"] = search.group(2)
            logged_sessions[pid]["user_exists"] = \
                    bool(logged_sessions[pid]["user_name"] in user_list)

        # fail count
        pattern = r"^Failed password"
        search = re.search(pattern,message)
        if (bool(search)):
            logged_sessions[pid]["fail_count"] += 1
        pattern = r"message repeated ([0-9]+) times: "+ \
                  r"\[ Failed password"
        search = re.search(pattern,message)
        if (bool(search)):
            logged_sessions[pid]["fail_count"] += int(search.group(1))

        # login status
        login_status = "Failed"
        pattern = r"^Accepted password"
        if (bool(re.search(pattern,message))):
            login_status = "Success"

        return logged_sessions,login_status


    def process_log(self,user_list,buffer_time,break_time):
        """Examines Log and extracts relevant data."""

        header = ["pid","fail_count","login_status", \
                  "first_date_time","last_date_time", \
                  "ip_address", \
                  "user_name","user_exists"]
        yield header


        # purpose:  enforce key-entries, allow cumulative 
        # entries (e.g. counters) and initial values (e.g. start time) 
        # for each session
        logged_sessions = dict()

        # filter lists
        service_whitelist = ["sshd"]
        message_blacklist = ["(sshd:session)","Server listening"]

        for line_log in self._read_log():

            # rough filter
            pattern = r"^(.+?)T(.+?)\s(.+?)\s(.+?):\s(.+?)$"
            line = re.findall(pattern,line_log)[0]
            # remove timezone
            date_time = line[0]+" "+line[1].split("+")[0]
            pid = "-1"
            service = line[3]
            message = line[4]


            # start accumulating entries after buffer time
            # (lifetime of ssh login-session before break_time)
            if (buffer_time > datetime.fromisoformat(date_time)):
                continue


            # resolve service, pid
            if ("[" in service):
                pattern = r"^(.+?)\[(.+?)\]$"
                service,pid = re.findall(pattern,service)[0]

            # filter service, messages
            if (service in service_whitelist and \
                not any([bl_entry in message \
                     for bl_entry in message_blacklist])):

                if (pid not in logged_sessions.keys()):
                    # initialization
                    logged_sessions[pid] = dict()
                    logged_sessions[pid]["fail_count"] = 0
                    logged_sessions[pid]["first_date_time"] = date_time

                logged_sessions,login_status = self.message_filter( \
                                                    logged_sessions, \
                                                    pid,message, \
                                                    user_list)

                # pass line only if key-entries are present
                if ("ip_address" not in logged_sessions[pid].keys() or \
                    "user_name" not in logged_sessions[pid].keys()):
                    continue


                # pass entries after break time
                if (break_time >= datetime.fromisoformat(date_time)):
                    continue


                # line according to header
                line_sorted = [pid, \
                               logged_sessions[pid]["fail_count"], \
                               login_status, \
                               logged_sessions[pid]["first_date_time"], \
                               date_time, \
                               logged_sessions[pid]["ip_address"], \
                               logged_sessions[pid]["user_name"], \
                               logged_sessions[pid]["user_exists"]]
                yield line_sorted


class CronJob:
    """
    A class to represent a cronjob.

    ...

    Attributes
    ----------
    _m : str
        value of minute field in crontab
    _h : str
        value of hour field in crontab
    _dom : str
        value of day-of-month field in crontab
    _mon : str
        value of month field in crontab
    _dow : str
        value of day-of-week field in crontab
    _exe : str
        executable/program called in crontab
    _file : str
        file executed in crontab
    active : bool
        cronjob entered in crontab (active) or not (inactive)

    Methods
    -------
    add_cronjob(sql_user):
        Adds cronjob to crontab.
    """

    def __init__(self,m,h,dom,mon,dow,exe,file):
        """Constructs all necessary attributes for the CronJob object."""

        self._m = m
        self._h = h
        self._dom = dom
        self._mon = mon
        self._dow = dow
        cmd = f"which {exe}"
        self._exe = subprocess.check_output(cmd,shell=True,text=True) \
                              .strip()
        self._file = file

        self.active = True
        cmd = "crontab -l"
        try:
            crontab = subprocess.check_output(cmd,shell=True,text=True, \
                                              stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            # if no crontab for user
            crontab = ""
    
        # check if cronjob for __file__ is set
        if (self._file not in crontab):
            self.active = False


    def add_cronjob(self,sql_user):
        """Adds cronjob to crontab."""

        print("Create a cronjob to execute this "+ \
              "run Append-mode regularly.\n")
        input("Press Enter to modify the exemplary cronjob "+ \
              "on the last line... ")

        # add cronjob to crontab
        job = f"{self._m}\t{self._h}\t"+ \
              f"{self._dom}\t{self._mon}\t{self._dow}\t"+ \
              f"{self._exe} {self._file}"
        cmd = f"(crontab -l; echo \"{job}\") | crontab -"
        print(cmd)
        subprocess.call(cmd,shell=True)
        # allow for modification of cronjob or approval
        cmd = "crontab -e"
        subprocess.call(cmd,shell=True)

        # store credentials in environment variable
        print("Please store your SQL-user credentials \n"+\
              "in the following way:\n"+ \
             f"export CHECK_LOGIN_USR=<username>\n"+ \
             f"export CHECK_LOGIN_PWD=<password>")


class Relation:
    """
    A class to represent a relation.
    
    ...

    Attributes
    ----------
    name : str
        name of the relation
    attrs : tuple of str
        attributes of the relation
    types : tuple of str
        data types of the attributes
    keys : tuple of str
        primary and foreign keys of the relation
    cstrs : tuple of str
        further constraints (e.g. NOT NULL, UNIQUE)
    level : str
        *"child": relation has foreign key values
         depending on the primary key of other relations
        *"parent": relation has no foreign key values
         depending on the primary key of other relations
    _sql_name : Identifier
        wrapped name variable
    _sql_attrs : tuple of Identifier
        wrapped attrs variable
    _sql_types : tuple of SQL-conform strings
        wrapped types variable
    _sql_cstrs : tuple of SQL-conform strings
        wrapped cstrs variable
    _attr_dict : dictionary
        translates lines of the input into attributes of the relation

    Instance Methods
    ----------------
    safe_attrs(is_sql=False):
        Returns non-key attributes.
    query_create():
        Constructs query to CREATE the relation.
    query_insert():
        Constructs query to INSERT tuples into the relation.
    fk_constraints():
        Sets foreign key constraints for the relation.
    create_attr_dict(src_attr):
        Creates dictionary to sort lines of input with attributes 
        src_attr to match attributes of the relation.
    convert_line(line):
        Converts line of input to properly fit into the database.

    Class Methods
    -------------
    create_table(header,content):
        Creates table representation of a query with header and content.
    print_table(table):
        Displays table representation of a query.
    write_table(table,fname):
        Writes table representation of a query to file fname.
    export_csv(content,fname):
        Export query as csv file.
    """

    def __init__(self,name,attrs,types,keys,cstrs,level):
        """Constructs necessary attributes of the Relation object."""

        self.name = name
        self.attrs = attrs
        self.types = types
        self.keys = keys
        self.cstrs = cstrs
        self.level = level

        self._sql_name = sql.Identifier(self.name)
        self._sql_attrs = tuple(map(sql.Identifier,self.attrs))
        self._sql_types = tuple(map(sql.SQL,self.types))
        self._sql_cstrs = tuple(map(sql.SQL,self.cstrs))

        self._attr_dict = {}


    def safe_attrs(self,is_sql=False):
        """Returns non-key attributes."""

        serial_indices = [self.keys.index(key) for key in self.keys 
                          if key!=""]
        if (is_sql):
            attrs = [attr for attr in self._sql_attrs 
                     if self._sql_attrs.index(attr) not in serial_indices]
        else:
            attrs = [attr for attr in self.attrs 
                     if self.attrs.index(attr) not in serial_indices]

        return attrs


    def query_create(self):
        """Constructs query to CREATE the relation."""

        # get primary key
        pkey = tuple(key for key in self.keys if key=="PRIMARY KEY")
        sql_pkey = tuple(map(sql.SQL,pkey))
        # combine parts of arguments
        args_zip = tuple(itertools.zip_longest(self._sql_attrs, \
                                               self._sql_types, \
                                               sql_pkey, \
                                               self._sql_cstrs, \
                                               fillvalue=sql.SQL("")))
        args_flat = sql.Composed(sql.SQL(', ').join( \
                                [sql.SQL(' ').join(tpl) for tpl in args_zip]))

        query = sql.SQL("CREATE TABLE IF NOT EXISTS {} ({});") \
               .format(self._sql_name,args_flat)
    
        return query


    def query_insert(self):
        """Constructs query to INSERT tuples into the relation."""

        # get attributes not directly or indirectly set via serial
        attrs = self.safe_attrs(is_sql=True)

        if (self.name != "sessions"):
            # parent relations
            query = sql.SQL("""INSERT INTO {} ({}) VALUES ({}) 
                               ON CONFLICT DO NOTHING;""").format( \
                    sql.Identifier(self.name), \
                    sql.SQL(', ').join(attrs), \
                    sql.SQL(', ').join(sql.Placeholder() * len(attrs)))
        else:
            # child relation
            query = sql.SQL("""INSERT INTO {} ({}) VALUES ({}) 
                               ON CONFLICT ({}) 
                               DO UPDATE SET ({}) = ({});""").format( \
                    sql.Identifier(self.name), \
                    sql.SQL(', ').join(attrs), \
                    sql.SQL(', ').join(sql.Placeholder() * len(attrs)), \
                    sql.SQL('first_date_time'), \
                    sql.SQL(', ').join(attrs),
                    sql.SQL(', ').join([sql.SQL('EXCLUDED.')+entry \
                            for entry in attrs]))
    
        return query


    def fk_constraints(self):
        """Sets foreign key constraints for the relation."""
   
        # get foreign keys
        fkeys = tuple(key for key in self.keys if key!="PRIMARY KEY")
        for fkey in fkeys:
            # name, primary key of other relation
            pkey_rel,pkey_attr = fkey.split()
            # foreign key of self
            fkey_attr = self.attrs[self.keys.index(fkey)]

            query = sql.SQL("""ALTER TABLE {} ADD CONSTRAINT {} 
                               FOREIGN KEY ({}) REFERENCES {} ({});""") \
                   .format(self._sql_name, \
                           sql.Identifier("fk_"+fkey_attr), \
                           sql.Identifier(fkey_attr), \
                           sql.Identifier(pkey_rel), \
                           sql.Identifier(pkey_attr))

            yield query


    def create_attr_dict(self,src_attr):
        """
        Creates dictionary to sort lines of input with attributes
        src_attr to match attributes of the relation.
        """

        # get attributes not directly or indirectly set via serial
        attrs = self.safe_attrs(is_sql=False)

        self._attr_dict = {attr:src_attr.index(attr) for attr in attrs}
    

    def convert_line(self,line):
        """
        Converts line of input to properly fit into the database.
        Task: Sorts line to match attributes of the relation.
        """

        line_sorted = [line[self._attr_dict[attr]] \
                       for attr in self._attr_dict.keys()]

        return line_sorted


    @staticmethod
    def create_table(header,content):
        """
        Creates table representation of a query with header 
        and content.
        """

        # setup
        table = Table(box=rich.box.ASCII)
        # columns
        for attr in header:
            table.add_column(attr)
        # add rows
        for entry in content:
            table.add_row(*entry)

        return table


    @staticmethod
    def print_table(table):
        """Displays table representation of a query."""

        console = Console()
        console.print(table)


    @staticmethod
    def write_table(table,fname):
        """Writes table representation of a query to file fname."""

        rich.print(table,file=fname)


    @staticmethod
    def export_csv(content,fname):
        """Export query as csv file."""

        try:
            with open(fname,"w",newline="") as csvfile:
                writer = csv.writer(csvfile,delimiter=",",quotechar="\"", \
                                    quoting=csv.QUOTE_MINIMAL)
                for line in content:
                    writer.writerow(line)
        except PermissionError:
            msg = f"Error: You lack permission to create {fname}."
            print(msg)


def check_db_exists(function):
    """Decorator checking if the database exists."""

    @wraps(function)
    def decorated(*args):
        try:
            function(*args)
        except psycopg2.errors.OperationalError:
            msg = "Error: Cannot find database."
            print(msg)
    return decorated


class Database:
    """
    A class to represent a Database.

    ...

    Attributes
    ----------
    name : str
        name of the Database
    file : LogFile object
        LogFile object fueling the Database file
    tests : str
        name of the file to store the Test-suite output
    relations : list of Relation objects
        relations contained in the Database

    Instance Methods
    ----------------
    create_database(sql_user):
        Creates database.
    initialize_relations():
        Initializes relations for the database.
    fetch_fk(child_relation,header,line,cursor):
        Fetch primary key values from parent relations 
        to insert them into foreign keys of child relations.
    setup_relations(sql_user,user_list):
        Creates and fills relations.
    append(sql_user,user_list):
        Appends data to the database.
    _if_instructions():
        Instructions for interface.
    _if_minmax(input_flat):
        Extract minmax statements from input.
    _if_assemble_query(self,user_attrs,where_clause, \
                       sort_clause,count_exist):
        Assemble query based on clauses.
    interface(sql_user):
        User command line interface.
    test_suite(sql_user):
        Provides sample queries and their output to verify 
        the created database.

    Class Methods
    -------------
    check_credentials(sql_user):
        Checks Username and Password.
    _if_read(input_quit):
        Read input from user.
    _if_export(input_flat,header,response):
        Export last query as csv file.
    _if_count(input_flat):
        Extract count statements from input.
    _if_sort(input_flat):
        Extract sort statements from input.
    _if_where(input_flat,minmax_exist,minmax_clause):
        Extract where statements from input.
        Includes minmax statements.
    """

    def __init__(self,name,file,tests):
        """Constructs necessary attributes of the Database object."""

        self.name = name
        self.file = file
        self.tests = tests
        self.relations = None


    @staticmethod
    def check_credentials(sql_user):
        """Checks Username and Password."""

        connected = False
        try:
            conn = psycopg2.connect(dbname="postgres",
                                    host="localhost",
                                    port="5432",
                                    user=sql_user.name,
                                    password=sql_user.passwd)
            conn.close()
        except psycopg2.errors.OperationalError:
            msg = "Error: Wrong Username or Password."
            print(msg)
        else:
            connected = True

        return connected


    def create_database(self,sql_user):
        """Creates database."""
    
        conn = psycopg2.connect(dbname="postgres",
                                host="localhost",
                                port="5432",
                                user=sql_user.name,
                                password=sql_user.passwd)
        conn.autocommit = True
        cursor = conn.cursor()
   
        # remove database if it exists already
        query = sql.SQL("DROP DATABASE IF EXISTS {};") \
               .format(sql.Identifier(self.name))
        cursor.execute(query)
        # create database
        query = sql.SQL("CREATE DATABASE {};") \
               .format(sql.Identifier(self.name))
        cursor.execute(query)
        
        cursor.close()
        conn.close()
    
    
    def initialize_relations(self):
        """Initializes relations for the database."""
    
        # initialize Relation objects
        # sessions
        name = "sessions"
        attrs = ("session_id","ip_id","user_id","pid","fail_count", \
                 "login_status","first_date_time","last_date_time")
        types = ("SERIAL","INTEGER","INTEGER","INTEGER","INTEGER", \
                 "TEXT","TIMESTAMP","TIMESTAMP")
        keys = ("PRIMARY KEY","ip_addresses ip_id","users user_id")
        cstrs = (*[""]*3,*["NOT NULL"]*3,"NOT NULL UNIQUE","NOT NULL")
        level = "child"
        sessions = Relation(name,attrs,types,keys,cstrs,level)
        # users
        name = "users"
        attrs = ("user_id","user_name","user_exists")
        types = ("SERIAL","TEXT","BOOLEAN")
        keys = ("PRIMARY KEY",)
        cstrs = ("","NOT NULL UNIQUE","NOT NULL")
        level = "parent"
        users = Relation(name,attrs,types,keys,cstrs,level)
        # ip_addresses
        name = "ip_addresses"
        attrs = ("ip_id","ip_address")
        types = ("SERIAL","INET")
        keys = ("PRIMARY KEY",)
        cstrs = ("","NOT NULL UNIQUE")
        level = "parent"
        ip_addresses = Relation(name,attrs,types,keys,cstrs,level)
        # relations
        self.relations = [users,ip_addresses,sessions]


    def fetch_fk(self,child_relation,header,line,cursor):
        """
        Fetch primary key values from parent relations 
        to insert them into foreign keys of child relations.
        """

        if (child_relation.level=="child"):

            # get child_id from child relation
            pkey_attr_child = tuple(child_relation.attrs[ii] 
                                    for ii,key in enumerate(child_relation.keys) 
                                    if key=="PRIMARY KEY")[0]
            unique_attr = tuple(child_relation.attrs[ii]
                                for ii,cstr in enumerate(child_relation.cstrs)
                                if "UNIQUE" in cstr)[0]
            query = sql.SQL("SELECT {} FROM {} WHERE {} = {};").format( \
                    sql.Identifier(pkey_attr_child), \
                    sql.Identifier(child_relation.name), \
                    sql.Identifier(unique_attr), \
                    sql.Placeholder())
            unique_val = line[header.index(unique_attr)]
            cursor.execute(query,(unique_val,))
            child_id = cursor.fetchone()


            fkeys = tuple(key for key in child_relation.keys 
                          if key!="PRIMARY KEY")
            for fkey in fkeys:
                rel_parent,pkey_attr_parent = fkey.split() 

                # get foreign key IDs
                unique_attr = tuple(rel.attrs[ii] \
                                    for rel in self.relations \
                                    for ii,cstr in enumerate(rel.cstrs) \
                                    if rel.name==rel_parent \
                                       and "UNIQUE" in cstr)[0]
                query = sql.SQL("SELECT {} FROM {} WHERE {} = {};").format( \
                        sql.Identifier(pkey_attr_parent), \
                        sql.Identifier(rel_parent), \
                        sql.Identifier(unique_attr), \
                        sql.Placeholder())
                unique_val = line[header.index(unique_attr)]
                cursor.execute(query,(unique_val,))
                parent_id = cursor.fetchone()

                # set foreign key IDs
                query = sql.SQL("UPDATE {} SET {} = {} WHERE {} = {};").format( \
                        sql.Identifier(child_relation.name), \
                        sql.Identifier(pkey_attr_parent), \
                        sql.Placeholder(), \
                        sql.Identifier(pkey_attr_child), \
                        sql.Placeholder())
                cursor.execute(query,(parent_id,child_id))


    @check_db_exists
    def setup_relations(self,sql_user,user_list):
        """Creates and fills relations."""
    
        conn = psycopg2.connect(dbname=self.name,
                                host="localhost",
                                port="5432",
                                user=sql_user.name,
                                password=sql_user.passwd)
        cursor = conn.cursor()
      
        # dummy value for time of last database entry
        buffer_time = datetime.now() - timedelta(days=14)
        # dummy value for lifetime of a ssh login session
        break_time = datetime.now() - timedelta(days=14)

        # start generator
        log_processed = self.file.process_log(user_list, \
                                              buffer_time,break_time)

        # create relations
        header = next(log_processed)
        for relation in self.relations:
            relation.create_attr_dict(header)
            query = relation.query_create()
            cursor.execute(query)

        # add constraints
        for relation in self.relations:
            for query in relation.fk_constraints():
                cursor.execute(query)
    
        # fill relations
        for line in log_processed:
            for relation in self.relations:
                line_converted = relation.convert_line(line)
                query = relation.query_insert()
                cursor.execute(query,line_converted)
                
                # fetch primary key values to foreign keys
                self.fetch_fk(relation,header,line,cursor)
    
        conn.commit()
        cursor.close()
        conn.close()
    
    
    @check_db_exists
    def append(self,sql_user,user_list):
        """Appends data to the database."""

        conn = psycopg2.connect(dbname=self.name,
                                host="localhost",
                                port="5432",
                                user=sql_user.name,
                                password=sql_user.passwd)
        cursor = conn.cursor()

        # time of last database entry
        query = """
                SELECT last_date_time from sessions 
                WHERE last_date_time = 
                (SELECT MAX(last_date_time) FROM sessions);
                """
        cursor.execute(query)
        break_time = cursor.fetchone()[0]

        # default parameters for ssh login-session
        # (see man sshd_config, CamelCase at underscore)
        max_auth_tries = 6
        login_grace_time = timedelta(minutes=2)
        delays = timedelta(minutes=1)
        dt = login_grace_time * max_auth_tries + delays
        # lifetime of a ssh login session before
        # time of last database entry
        buffer_time = break_time - dt
       
        # start generator
        log_processed = self.file.process_log(user_list, \
                                              buffer_time,break_time)

        # create association between Log file and relations
        header = next(log_processed)
        for relation in self.relations:
            relation.create_attr_dict(header)

        # append to relations
        for line in log_processed:
            for relation in self.relations:
                line_converted = relation.convert_line(line)
                query = relation.query_insert()
                cursor.execute(query,line_converted)

                # fetch primary key values to foreign keys
                self.fetch_fk(relation,header,line,cursor)

        conn.commit()
        cursor.close()
        conn.close()


    def _if_instructions(self):
        """Instructions for interface."""

        # get attributes not directly or indirectly set via serial
        attrs_avail = []
        for relation in self.relations:
            attrs = relation.safe_attrs(is_sql=False)
            attrs_avail = [*attrs_avail,*attrs]
        # separate for formatting
        attrs_format = [attrs_avail[ii:min(ii+4,len(attrs_avail))] 
                        for ii in range(0,len(attrs_avail),4)]

        # instructions
        print("\nAvailable attributes:\n"+ \
              ",\n".join([", ".join(attr)
                          for attr in attrs_format]))
        filters = """
                  Available filters:
                  > Restrict arguments: arg <, >, <=, >=, =, != value
                  > Range: arg<value_upper, arg>value_lower
                  > Simple functions: max(arg), min(arg)
                  > Counting: count(arg), count(arg=value)
                  > Sorting: asc(arg), desc(arg)
                  > Date: 'yyyy-mm-dd'
                  > Time: 'HH:[MM:[SS]]'
                  > String value: 'value'
                  > Case-sensitive Regex: arg ~ regex
                  """
        print(textwrap.dedent(filters))
        print("Export previous output to csv: export filename")
        print("Syntax: statement_1, statement_2, ... statment_n;\n")
        print("Press q+Enter to quit.\n")


    @staticmethod
    def _if_read(input_quit):
        """Read input from user."""

        input_list = []
        input_flat = []
        while True:
            line = input("??? ")
            input_list.append(line)

            # quit
            if (input_list[0]=="q"):
                input_quit = "q"
                break

            # collect input
            if (";" in line):
                line = line[:line.index(";")]
                input_list[-1] = line
                # list of list with statements
                input_flat = list(
                                 map(str.strip, \
                                     " ".join(input_list).split(",") \
                                 ) \
                             )
                input_flat = [[flt] for flt in input_flat]
                break

        return input_flat, input_quit


    @staticmethod
    def _if_export(input_flat,header,response):
        """Export last query as csv file."""

        exported = False
        if ("export" in input_flat[0][0]):
            fname = input_flat[0][0].split()[1].lstrip(".")
            file_type = ""
            pattern = r"\.csv$"
            search = re.search(pattern,fname)
            if (not bool(search)):
                file_type = ".csv"

            if (not bool(header) or not bool(response)):
                print(f"Cannot export to {fname+file_type} "+ \
                       "without query.")
            elif (fname==""):
                print("Invalid filename.")
            else:
                Relation.export_csv([header,*response],fname+file_type)
                print(f"Query exported as {fname+file_type}.")

            exported = True

        return exported


    @staticmethod
    def _if_count(input_flat):
        """Extract count statements from input."""

        cts = "count"
        count_dict = {input_flat.index(flt): \
                      [re.search(cts+r"\((.+?)\)",flt[0]).group(1), \
                       cts] \
                      for flt in input_flat \
                      if cts+"(" in flt[0]}
        count_exist = bool(count_dict)

        for key in count_dict.keys():
            input_flat[key] = [count_dict[key][0]]

        return input_flat, count_exist


    def _if_minmax(self,input_flat):
        """Extract minmax statements from input."""

        minmax = ("min","max")
        minmax_dict = {input_flat.index(flt): \
                       [re.search(mm+r"\((.+?)\)",flt[0]).group(1), \
                        mm] \
                       for flt in input_flat \
                       for mm in minmax \
                       if mm+"(" in flt[0]}
        minmax_exist = bool(minmax_dict)

        for key in minmax_dict.keys():
            input_flat[key] = [minmax_dict[key][0]]

        if (minmax_exist):

            minmax_lst = [sql.SQL("{} = (SELECT {}({}) FROM {})").format( \
                          sql.Identifier(mm[0]), \
                          sql.SQL(mm[1].upper()), \
                          sql.Identifier(mm[0]), \
                          sql.Identifier(relation.name)) \
                          for relation in self.relations \
                          for mm in minmax_dict.values() \
                          if mm[0] in relation.safe_attrs(is_sql=False)]

            minmax_clause = sql.SQL(' OR ').join(minmax_lst)
        else:
            minmax_clause = sql.SQL('')

        return input_flat,minmax_exist,minmax_clause


    @staticmethod
    def _if_sort(input_flat):
        """Extract sort statements from input."""

        sorts = ("asc","desc")
        sort_dict = {input_flat.index(flt): \
                     [re.search(sort+r"\((.+?)\)",flt[0]).group(1), \
                      sort] \
                     for flt in input_flat \
                     for sort in sorts \
                     if sort+"(" in flt[0]}
        sort_exist = bool(sort_dict)

        for key in sort_dict.keys():
            input_flat[key] = [sort_dict[key][0]]

        if (sort_exist):

            sorting = [sql.SQL("ORDER BY {} {}").format( \
                         sql.Identifier(sort[0]), \
                         sql.SQL(sort[1].upper())) \
                         for sort in sort_dict.values()]

            sort_clause = sql.SQL(', ').join(sorting)
        else:
            sort_clause = sql.SQL("")

        return input_flat,sort_clause


    @staticmethod
    def _if_where(input_flat,minmax_exist,minmax_clause):
        """
        Extract where statements from input.
        Includes minmax statements.
        """

        ops = ("<",">","<=",">=","=","!=","~")
        # decompose filters
        where_dict = {input_flat.index(flt): [*flt[0].split(op),op] \
                      for flt in input_flat \
                      for op in ops \
                      if op in flt[0]}
        where_exist = bool(where_dict)

        for key in where_dict.keys():
            input_flat[key] = where_dict[key]

        if (where_exist):
            comparisons = [sql.SQL("{} {} {}").format( \
                           sql.Identifier(flt[0]), \
                           sql.SQL(flt[2]), \
                           sql.SQL(flt[1])) \
                           for flt in input_flat if (len(flt)==3)]
   
            if (minmax_exist):
                where_clause = sql.SQL("WHERE {} AND ({})").format( \
                               sql.SQL(' AND ').join(comparisons), \
                               minmax_clause)
            else:
                where_clause = sql.SQL("WHERE {}").format( \
                               sql.SQL(' AND ').join(comparisons))
        elif (minmax_exist):
            where_clause = sql.SQL("WHERE ({})").format( \
                           minmax_clause)
        else:
            where_clause = sql.SQL("")

        return input_flat,where_clause


    def _if_assemble_query(self,user_attrs,where_clause, \
                           sort_clause,count_exist):
        """Assemble query based on clauses."""

        # list of attributes with associated relations
        # in format "relation.attribute"
        user_relations = []
        select_args = []
        for relation in self.relations:
            user_relation_attrs = [sql.Identifier(relation.name,attr) \
                                   for attr in user_attrs \
                                   if attr in relation.safe_attrs(is_sql=False)]
            if (bool(user_relation_attrs)):
                user_relations.append(relation.name)
                select_args = [*select_args,*user_relation_attrs]

        # modify if count present
        if (count_exist):
            sort_clause = sql.SQL("")
            select_args = [sql.SQL("COUNT(*)")]

        # assemble query
        if (len(user_relations)==1):
            query = sql.SQL("SELECT {} FROM {} {} {};").format( \
                    sql.SQL(', ').join(select_args), \
                    sql.Identifier(user_relations[0]), \
                    where_clause, \
                    sort_clause)
        elif (len(user_relations)>1):
            sessions = [relation for relation in self.relations \
                        if relation.name=="sessions"][0]
            join_clause = [sql.SQL(" INNER JOIN {} ON {} = {}").format( \
                           sql.Identifier(key.split()[0]), \
                           sql.Identifier(key.split()[0],key.split()[1]), \
                           sql.Identifier('sessions',key.split()[1])) \
                           for key in sessions.keys \
                           if key.split()[0] in user_relations]

            query = sql.SQL("SELECT {} FROM {} {} {} {};").format( \
                    sql.SQL(', ').join(select_args), \
                    sql.Identifier('sessions'), \
                    sql.SQL(' ').join(join_clause), \
                    where_clause, \
                    sort_clause)
        else:
            query = sql.SQL("SELECT unknown_attr FROM sessions")

        return query


    @check_db_exists
    def interface(self,sql_user):
        """User command line interface."""
    
        conn = psycopg2.connect(dbname=self.name,
                                host="localhost",
                                port="5432",
                                user=sql_user.name,
                                password=sql_user.passwd)
        cursor = conn.cursor()
        
        input_quit = ""
        header = ()
        response = []

        while (input_quit!="q"):
      
            self._if_instructions()

            input_flat,input_quit = self._if_read(input_quit)
            if (input_quit=="q"):
                continue

            exported = self._if_export(input_flat,header,response)
            if (exported):
                continue

            input_flat,count_exist = self._if_count(input_flat)
            input_flat,minmax_exist,minmax_clause = self._if_minmax(input_flat)
            input_flat,sort_clause = self._if_sort(input_flat)
            input_flat,where_clause = self._if_where(input_flat, \
                                                     minmax_exist, \
                                                     minmax_clause)

            # unique attributes
            user_attrs = list(set([flt[0] for flt in input_flat]))

            query = self._if_assemble_query(user_attrs,where_clause, \
                                            sort_clause,count_exist)

            # execute query
            cursor.execute('SAVEPOINT sp;')
            try:
                cursor.execute(query)
            except psycopg2.errors.UndefinedColumn:
                msg = "Error: Cannot find attribute."
                print(msg)
                cursor.execute('ROLLBACK TO SAVEPOINT sp;')
            except psycopg2.errors.UndefinedTable:
                msg = "Error: Cannot find table."
                print(msg)
                cursor.execute('ROLLBACK TO SAVEPOINT sp;')
            else:
                # display table
                header = tuple(name[0] for name in cursor.description)
                response = [tuple(map(str,entry)) for entry in cursor.fetchall()]
                table = Relation.create_table(header,response)
                Relation.print_table(table)

        conn.commit()
        cursor.close()
        conn.close()

    
    @check_db_exists
    def test_suite(self,sql_user):
        """
        Provides sample queries and their output to verify 
        the created database.
        """
    
        tasks = ["All relevant information", \
                 "All existing Users", \
                 "Fail-counts for users and IP-addresses"]
    
        queries = ["""
                   SELECT sessions.pid, users.user_name, users.user_exists, 
                   ip_addresses.ip_address, 
                   sessions.first_date_time, sessions.last_date_time, 
                   sessions.fail_count, sessions.login_status
                   FROM sessions 
                   INNER JOIN users ON sessions.user_id = users.user_id 
                   INNER JOIN ip_addresses ON sessions.ip_id = ip_addresses.ip_id;
                   """,
                   """
                   SELECT sessions.pid, users.user_name, ip_addresses.ip_address, 
                   sessions.first_date_time, sessions.last_date_time
                   FROM sessions 
                   INNER JOIN users ON sessions.user_id = users.user_id 
                   INNER JOIN ip_addresses ON sessions.ip_id = ip_addresses.ip_id
                   WHERE users.user_exists IS TRUE;
                   """,
                   """
                   SELECT users.user_name, ip_addresses.ip_address, 
                   sessions.fail_count, users.user_exists
                   FROM sessions 
                   JOIN users ON sessions.user_id = users.user_id 
                   JOIN ip_addresses ON sessions.ip_id = ip_addresses.ip_id;
                   """]
    
        conn = psycopg2.connect(dbname=self.name,
                                host="localhost",
                                port="5432",
                                user=sql_user.name,
                                password=sql_user.passwd)
        cursor = conn.cursor()
    
        # table representation
        try:
            with open(self.tests,"w",newline="") as test_file:
        
                for ii in range(len(tasks)):
                    test_file.write("\n" \
                                   +textwrap.dedent(tasks[ii]).strip() \
                                   +":\n")
                    cursor.execute(queries[ii])
                    header = tuple(name[0] for name in cursor.description)
                    response = [tuple(map(str,entry)) \
                                for entry in cursor.fetchall()]
                    table = Relation.create_table(header,response)
                    test_file.write(textwrap.dedent(queries[ii])+"\n")
                    Relation.write_table(table,test_file)
    
        except PermissionError:
            msg = f"Error: You lack permission to create {fname}."
            print(msg)

        # csv file
        cursor.execute(queries[0])
        header = list(name[0] for name in cursor.description)
        response = [list(map(str,entry)) \
                    for entry in cursor.fetchall()]
        Relation.export_csv([header,*response], \
                            self.tests.split(".")[0]+".csv")
    
        conn.commit()
        cursor.close()
        conn.close()


@check_db_exists
def interactive_queries(sql_user,db_name):
    """Run queries interactively."""

    conn = psycopg2.connect(dbname=db_name,
                            host="localhost",
                            port="5432",
                            user=sql_user.name,
                            password=sql_user.passwd)
    cursor = conn.cursor()

    input_quit = ""
    while (input_quit!="q"):
    
        # read query
        print("\nEnter query or q+Enter to quit:")
        input_list = []
        while True:
            line = input()
            input_list.append(line)
            # quit
            if (input_list[0]=="q"):
                input_quit = "q"
                break
            # collect input
            if (";" in line):
                line = line[:line.index(";")+1]
                input_list[-1] = line
                break
            input_list = []
        if (input_quit=="q"):
            continue

        query = " ".join(input_list)

        # execute query
        cursor.execute('SAVEPOINT sp;')
        try:
            cursor.execute(query)
        except psycopg2.errors.UndefinedColumn:
            msg = "Error: Cannot find attribute."
            print(msg)
            cursor.execute('ROLLBACK TO SAVEPOINT sp;')
        except psycopg2.errors.UndefinedTable:
            msg = "Error: Cannot find table."
            print(msg)
            cursor.execute('ROLLBACK TO SAVEPOINT sp;')
        else:
            # display table
            header = tuple(name[0] for name in cursor.description)
            response = [tuple(map(str,entry)) for entry in cursor.fetchall()]
            table = Relation.create_table(header,response)
            Relation.print_table(table)
    
    conn.commit()
    cursor.close()
    conn.close()


class SQLUser:
    """
    A class to represent the user.

    ...

    Attributes
    ----------
    name : str
        name of the user
    passwd : str
        password of the user

    Methods
    -------
    get_login():
        Gets login data for SQL server interactively.
    get_login_env():
        Gets login data for SQL server from environment variables.
    """

    def __init__(self):
        """Constructs all necessary attributes for the User object."""

        self.name = ""
        self.passwd = ""


    def get_login(self):
        """Gets login data for SQL server interactively."""

        self.name = input("Username: ")
        self.passwd = getpass("Password: ")


    def get_login_env(self):
        """Gets login data for SQL server from environment variables."""

        self.name = os.getenv('CHECK_LOGIN_USR')
        self.passwd = os.getenv('CHECK_LOGIN_PWD')


class User:
    """
    A class to represent the user.

    ...

    Attributes
    ----------
    _name : str
        name of the user
    home : str
        home-directory of the user
    list : list of str
        list of users on the system
    """

    def __init__(self):
        """Constructs all necessary attributes for the User object."""

        cmd = "whoami"
        self._name = subprocess.check_output(cmd,shell=True,text=True) \
                               .strip()

        if (self._name == "root"):
            # root user: logs in accessible directory
            self.home = "/home"
        else:
            # regular user: logs in own home-directory
            self.home = f"/home/{self._name}"

        # list of users
        shell_blacklist = ["nologin","false"]
        user_blacklist = ["sync","postgres"]
        self.list = []
        fname = "/etc/passwd"
        with open(fname,newline="") as userfile:
            reader = csv.reader(userfile, delimiter = ":")
            for line in reader:
                if ((not any([shell in line[6] \
                     for shell in shell_blacklist]))
                     and (not any([user in line[0] \
                     for user in user_blacklist]))):
                    self.list.append(line[0])


def main():
    """
    Create-mode:
        *Creates database, creates and fills relations.
        *Runs a set of SQL-queries to check the database.
    Append-mode: 
        Append data to the database.
    Interactive-mode:
        Processes queries on created database.
    User-mode:
        Display data through a simple CLI.
    """

    print("\n| checkLogins |\n")

    if (len(sys.argv)==2):
        mode = sys.argv[1]
    else:
        mode = "-u"

    log_file = LogFile("auth.log","/var/log")
    user = User()
    log_file.copy_log(user.home)
    
    db_name = "auth_logs"
    db_tests = "auth_tests.txt"
    db = Database(db_name,log_file,db_tests)

    # get login data
    sql_user = SQLUser()
    if (mode != "--cron_job"):
        print("Provide login details for the database.")
        connected = False
        while (not connected):
            sql_user.get_login()
            connected = db.check_credentials(sql_user)
    else:
        sql_user.get_login_env()


    if (mode=="-c" or mode=="--create"):
        print("\n| Create-mode |\n")

        try: 
            print(f"Creating the database \"{db_name}\"...")
            db.create_database(sql_user)
            print("Database created.\n")

            print("Creating and filling the database relations...")
            db.initialize_relations()
            db.setup_relations(sql_user,user.list)
            print("Database relations created and filled.\n")

        except psycopg2.errors.OperationalError:
            msg = "Error: Database cannot be rebuild " \
                 +"since it is currently in use.\n" \
                 +"Using existing database."
            print(msg)

        print("Creating sample queries and output...")
        db.test_suite(sql_user)
        print("Created sample queries and output.")

    elif (mode=="-a" or mode=="--append"):
        print("\n| Append-mode |\n")

        print("Appending to database relations...")
        db.initialize_relations()
        db.append(sql_user,user.list)
        print("Database extended.\n")

        print("Creating sample queries and output...")
        db.test_suite(sql_user)
        print("Created sample queries and output.\n")

    elif (mode=="-i" or mode=="--interactive"):
        print("\n| Interactive-mode |\n")

        interactive_queries(sql_user,db.name)

    elif (mode=="-u" or mode=="--user"):
        print("\n| User-mode |\n")

        db.initialize_relations()
        db.interface(sql_user)

    elif (mode=="-s" or mode=="--setup"):
        print("\n| Setup-mode |\n")

        # append to database from cron-job
        db.initialize_relations()
        db.append(sql_user,user.list)

        # setup cronjob
        cronjob = CronJob("0","0","*","*","*","python3",f"{__file__} --cron_job")
        if (not cronjob.active):
            cronjob.add_cronjob(sql_user)

    elif (mode=="--cron_job"):
        # append to database from cron-job
        db.initialize_relations()
        db.append(sql_user,user.list)


    # clean up
    log_file.rm_log()


if (__name__ == "__main__"):
    main()
