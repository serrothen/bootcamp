#!/usr/bin/env python3
"""
OverVIEW: Create a database for AlphaTech Consulting.
Create-mode:
    *Creates database, creates and fills relations.
    *Runs a set of SQL-queries to check the database.
Interactive-mode:
    Processes queries on created database.

Classes:

    Relation
    Database
    User
"""

# Python Standard Library
import sys
from getpass import getpass
import csv
import itertools
import textwrap
from functools import wraps
from datetime import date
import readline

# Third-party libraries
import psycopg2
from psycopg2 import sql
import rich
from rich.table import Table
from rich.console import Console


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
    _check_date(old_date):
        Expand year in old_date to four digits while assuming 
        the youngest timespan possible (e.g. 18 years rather 
        than 100 years).
    create_table(header,content):
        Creates table representation of a query with header and content.
    print_table(table):
        Displays table representation of a query.
    write_table(table,fname):
        Writes table representation of a query to file fname.
    export_csv(content,fname):
        Export query as csv file.
    """

    def __init__(self,name,attrs,types,keys,cstrs):
        """Constructs necessary attributes of the Relation object."""

        self.name = name
        self.attrs = attrs
        self.types = types
        self.keys = keys
        self.cstrs = cstrs

        self._sql_name = sql.Identifier(self.name)
        self._sql_attrs = tuple(map(sql.Identifier,self.attrs))
        self._sql_types = tuple(map(sql.SQL,self.types))
        self._sql_cstrs = tuple(map(sql.SQL,self.cstrs))

        self._attr_dict = {}


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
       
        query = sql.SQL("""INSERT INTO {} ({}) VALUES ({}) 
                           ON CONFLICT DO NOTHING;""").format( \
                sql.Identifier(self.name), \
                sql.SQL(', ').join(self._sql_attrs), \
                sql.SQL(', ').join(sql.Placeholder() * len(self.attrs)))
    
        return query


    def fk_constraints(self):
        """Sets foreign key constraints for the relation."""
   
        # get foreign keys
        fkeys = tuple(key for key in self.keys if key!="PRIMARY KEY")
        for fkey in fkeys:
            # name, primary key of other relation
            pkey_rel = fkey.split()[0]
            pkey_attr = fkey.split()[1]
            # foreign key of self
            fkey_attr = self.attrs[self.keys.index(fkey)]

            query = sql.SQL("""ALTER TABLE {} ADD CONSTRAINT {} 
                               FOREIGN KEY ({}) REFERENCES {} ({}) 
                               INITIALLY DEFERRED;""") \
                   .format(self._sql_name, \
                           sql.Identifier("fk_"+fkey_attr), \
                           sql.Identifier(fkey_attr), \
                           sql.Identifier(pkey_rel), \
                           sql.Identifier(pkey_attr))

            yield query


    @staticmethod
    def _check_date(old_date):
        """
        Expand year in old_date to four digits while assuming 
        the youngest timespan possible (e.g. 18 years rather 
        than 100 years).
        """
        
        new_date = old_date
        date_list = old_date.split("/")

        # check if digits in year are missing
        if (len(date_list[2])<4):
            year_20 = int("20"+date_list[2])
            current_year = date.today().year

            # check if year has already passed
            if ((year_20-current_year) > 0):
                date_list[2] = "19"+date_list[2]
            else:
                date_list[2] = year_20

            new_date = "/".join(date_list)

        return new_date


    def create_attr_dict(self,src_attr):
        """
        Creates dictionary to sort lines of input with attributes
        src_attr to match attributes of the relation.
        """

        self._attr_dict = {attr:src_attr.index(attr) for attr in self.attrs}
    

    def convert_line(self,line):
        """
        Converts line of input to properly fit into the database.
        Tasks: 
            *Sorts line to match attributes of the relation.
            *Modifies the date to handle a postgreSQL implementation 
             choice (years with less than four digits are adjusted to 
             be closest to 2020, see
             https://www.postgresql.org/docs/current/functions-formatting.html)
        """

        line_sorted = [line[self._attr_dict[attr]] \
                       for attr in self._attr_dict.keys()]
        line_checked = [Relation._check_date(line_sorted[ii]) \
                        if (self.types[ii]=="DATE") else line_sorted[ii] \
                        for ii in range(len(line_sorted))]

        return line_checked


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


def check_db_connection(function):
    """Decorator checking if the database exists."""

    @wraps(function)
    def decorated(*args):
        try:
            function(*args)
        except psycopg2.errors.OperationalError:
            msg = "Error: Connection to database failed."
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
    fname : str
        name of the file fueling the Database file
    tests : str
        name of the file to store the Test-suite output
    relations : list of Relation objects
        relations contained in the Database

    Instance Methods
    ----------------
    create_database(user):
        Creates database.
    initialize_relations():
        Initializes relations for the database.
    setup_relations(user):
        Creates and fills relations.
    add_constraints(user):
        Adds constraints to database.
    test_suite(user):
        Provides sample queries and their output to verify 
        the created database.

    Class Methods
    -------------
    check_credentials(user):
        Checks Username and Password.
    """

    def __init__(self,name,fname,tests):
        """Constructs necessary attributes of the Database object."""

        self.name = name
        self.fname = fname
        self.tests = tests
        self.relations = None


    @staticmethod
    def check_credentials(user):
        """Checks Username and Password."""

        connected = False
        try:
            conn = psycopg2.connect(dbname="postgres",
                                    host="localhost",
                                    port="5432",
                                    user=user.name,
                                    password=user.passwd)
            conn.close()
        except psycopg2.errors.OperationalError:
            msg = "Error: Wrong Username or Password."
            print(msg)
        else:
            connected = True

        return connected


    def create_database(self,user):
        """Creates database."""
    
        conn = psycopg2.connect(dbname="postgres",
                                host="localhost",
                                port="5432",
                                user=user.name,
                                password=user.passwd)
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
        # employees
        name = "employees"
        attrs = ("EmpID","PositionID","DeptID","ManagerID","ProjectID", \
                 "EmployeeName","Salary","DateofHire","State","Zip", \
                 "DateofBirth","GenderID","Sex")
        types = (*["INT"]*5,"TEXT","MONEY","DATE","CHAR(2)","INT", \
                 "DATE","INT","CHAR(1)")
        keys = ("PRIMARY KEY","positions PositionID","departments DeptID", \
                "managers ManagerID", "projects ProjectID")
        cstrs = ("",*["NOT NULL"]*(len(attrs)-1))
        employees = Relation(name,attrs,types,keys,cstrs)
        # departments
        name = "departments"
        attrs = ("DeptID","Department")
        types = ("INT","TEXT")
        keys = ("PRIMARY KEY",)
        cstrs = ("","NOT NULL UNIQUE")
        departments = Relation(name,attrs,types,keys,cstrs)
        # positions
        name = "positions"
        attrs = ("PositionID","Position")
        types = ("INT","TEXT")
        keys = ("PRIMARY KEY",)
        cstrs = ("","NOT NULL UNIQUE")
        positions = Relation(name,attrs,types,keys,cstrs)
        # managers
        name = "managers"
        attrs = ("ManagerID","ManagerName")
        types = ("INT","TEXT")
        keys = ("PRIMARY KEY",)
        cstrs = ("","NOT NULL UNIQUE")
        managers = Relation(name,attrs,types,keys,cstrs)
        # projects
        name = "projects"
        attrs = ("ProjectID","ClientID","Project", \
                 "ProductOwner","ProjectBudget")
        types = (*["INT"]*2,*["TEXT"]*2,"MONEY")
        keys = ("PRIMARY KEY","clients ClientID")
        cstrs = ("","NOT NULL","NOT NULL UNIQUE",*["NOT NULL"]*2)
        projects = Relation(name,attrs,types,keys,cstrs)
        # clients
        name = "clients"
        attrs = ("ClientID","Client","ClientCEO","ClientAddress")
        types = ("INT",*["TEXT"]*3)
        keys = ("PRIMARY KEY",)
        cstrs = ("","NOT NULL UNIQUE",*["NOT NULL"]*2)
        clients = Relation(name,attrs,types,keys,cstrs)
        # relations
        self.relations = [employees,departments,positions,managers, \
                          projects,clients]


    @check_db_connection
    def setup_relations(self,user):
        """Creates and fills relations."""
    
        conn = psycopg2.connect(dbname=self.name,
                                host="localhost",
                                port="5432",
                                user=user.name,
                                password=user.passwd)
        cursor = conn.cursor()
       
        try:
            with open(self.fname,newline="") as csvfile:
                reader = csv.reader(csvfile, delimiter = ",")
    
                # create relations
                header = next(reader)
                for relation in self.relations:
                    relation.create_attr_dict(header)
                    query = relation.query_create()
                    cursor.execute(query)
    
                # fill relations
                for line in reader:
                    for relation in self.relations:
                        line_converted = relation.convert_line(line)

                        query = relation.query_insert()
                        cursor.execute(query,line_converted)
    
        except FileNotFoundError:
            msg = f"Error: The file {csvfile} does not exist."
            print(msg)
        except PermissionError:
            msg = f"Error: You lack permission to read {csvfile}."
            print(msg)
    
        conn.commit()
        cursor.close()
        conn.close()
    
    
    @check_db_connection
    def add_constraints(self,user):
        """Adds constraints to database."""
    
        conn = psycopg2.connect(dbname=self.name,
                                host="localhost",
                                port="5432",
                                user=user.name,
                                password=user.passwd)
        cursor = conn.cursor()
      
        for relation in self.relations:
            for query in relation.fk_constraints():
                cursor.execute(query)
        
        conn.commit()
        cursor.close()
        conn.close()
    
    
    @check_db_connection
    def test_suite(self,user):
        """
        Provides sample queries and their output to verify 
        the created database.
        """
    
        tasks = ["Name, birthday and sex of the Sales department", \
                 "Female share", \
                 "Gender pay gap", \
                 "Hiring over three years", \
                 "Age of oldest employee", \
                 "Average age", \
                 "Total salary for Apple projects", \
                 """
                 Name, position and department of employees
                 working on the projects \"Google Cloud Platform\"
                 and \"AWS\"
                 """, \
                 "Positions in the Software Engineering department", \
                 "Number of Managers", \
                 "Management team"]
    
        queries = ["""
                   SELECT employees.\"EmployeeName\", employees.\"DateofBirth\", employees.\"Sex\" 
                   FROM employees 
                   INNER JOIN departments ON employees.\"DeptID\" = departments.\"DeptID\" 
                   WHERE departments.\"Department\" = 'Sales';
                   """,
                   """
                   SELECT TO_CHAR(CAST(COUNT(*) FILTER (WHERE \"Sex\"='F') AS decimal)/(COUNT(*)),'0.99') 
                   AS \"Ratio Woman/Total\" FROM employees;
                   """,
                   """
                   SELECT CAST(AVG(\"Salary\"::numeric) FILTER (WHERE \"Sex\"='F') AS MONEY) 
                   AS \"Average Salary Women\", 
                   CAST(AVG(\"Salary\"::numeric) FILTER (WHERE \"Sex\"='M') AS MONEY)
                   AS \"Average Salary Man\" FROM employees;
                   """,
                   """
                   SELECT COUNT(*) FROM employees WHERE \"DateofHire\" >= (CURRENT_DATE - INTERVAL '3 year');
                   """,
                   """
                   SELECT TO_CHAR(AGE(CURRENT_DATE, MIN(\"DateofBirth\")), 
                   'YY "Years" mm "Months" DD "Days"') 
                   AS \"Age of oldest employee\" FROM employees;
                   """,
                   """
                   SELECT TO_CHAR(AVG(AGE(CURRENT_DATE, \"DateofBirth\")), 
                   'YY "Years" mm "Months" DD "Days"') 
                   AS \"Average Age\" FROM employees;
                   """,
                   """
                   SELECT SUM(employees.\"Salary\") AS \"Total salary for Apple projects\" FROM employees 
                   INNER JOIN projects ON employees.\"ProjectID\"=projects.\"ProjectID\" 
                   INNER JOIN clients ON projects.\"ClientID\"=clients.\"ClientID\" 
                   WHERE clients.\"Client\"='Apple';
                   """,
                   """
                   SELECT employees.\"EmployeeName\", positions.\"Position\", departments.\"Department\" 
                   FROM employees 
                   INNER JOIN positions ON employees.\"PositionID\"=positions.\"PositionID\" 
                   INNER JOIN departments ON employees.\"DeptID\"=departments.\"DeptID\" 
                   INNER JOIN projects ON employees.\"ProjectID\"=projects.\"ProjectID\" 
                   WHERE projects.\"Project\"='Google Cloud Platform' OR projects.\"Project\"='AWS';
                   """,
                   """
                   SELECT DISTINCT positions.\"Position\" AS \"Positions\" FROM employees 
                   INNER JOIN positions ON employees.\"PositionID\"=positions.\"PositionID\" 
                   INNER JOIN departments ON employees.\"DeptID\"=departments.\"DeptID\" 
                   WHERE departments.\"Department\"='Software Engineering';
                   """,
                   """
                   SELECT COUNT(*) AS \"Number of Managers\" FROM employees 
                   INNER JOIN managers ON employees.\"EmployeeName\"=managers.\"ManagerName\";
                   """,
                   """
                   SELECT managers.\"ManagerName\", positions.\"Position\", employees.\"Salary\" 
                   FROM employees 
                   INNER JOIN managers ON employees.\"EmployeeName\"=managers.\"ManagerName\" 
                   INNER JOIN positions ON employees.\"PositionID\"=positions.\"PositionID\";
                   """]
    
        conn = psycopg2.connect(dbname=self.name,
                                host="localhost",
                                port="5432",
                                user=user.name,
                                password=user.passwd)
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


class User:
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
    get_login:
        Gets login data for SQL server.
    """

    def __init__(self):
        """Constructs all necessary attributes for the User object."""

        self.name = ""
        self.passwd = ""


    def get_login(self):
        """Gets login data for SQL server."""

        self.name = input("Username: ")
        self.passwd = getpass("Password: ")


@check_db_connection
def interactive_queries(user,db_name):
    """Run queries interactively."""

    conn = psycopg2.connect(dbname=db_name,
                            host="localhost",
                            port="5432",
                            user=user.name,
                            password=user.passwd)
    cursor = conn.cursor()
    
    input_quit = ""
    while (input_quit!="q"):
    
        # read query
        print("Enter query:")
        input_list = []
        while True:
            line = input()
            input_list.append(line)
            if (";" in line):
                line = line[:line.index(";")+1]
                input_list[-1] = line
                break
        query = " ".join(input_list)
  
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
    
        input_quit = input("\nPress q+Enter to quit or Enter to continue... ")
    
    conn.commit()
    cursor.close()
    conn.close()


def main():
    """
    Create-mode:
        *Creates database, creates and fills relations.
        *Runs a set of SQL-queries to check execution.
    Interactive-mode:
        Processes queries on created database.
    """

    print("\n| OverVIEW of AlphaTech Consulting |\n")

    db_name = "alphatech"
    db_fname = "AlphaTechConsultigEmployees.csv"
    db_tests = "AlphaTech_tests.txt"
    db = Database(db_name,db_fname,db_tests)

    # get login data
    print("Provide login details for the database.")
    user = User()
    connected = False
    while (not connected):
        user.get_login()
        connected = db.check_credentials(user)

    if (len(sys.argv)==2):
        mode = sys.argv[1]
    else:
        mode = "-i"

    if (mode=="-c" or mode=="--create"):
        print("\n| Create-mode |\n")

        try: 
            # create database
            print(f"Creating the database \"{db_name}\"...")
            db.create_database(user)
            print("Database created.\n")
            
            # create and fill relations
            print("Creating and filling the database relations...")
            db.initialize_relations()
            db.setup_relations(user)
            print("Database relations created and filled.\n")
            
            # set foreign key constraints
            print("Adding constraints...")
            db.add_constraints(user)
            print("Constraints added.\n")

        except psycopg2.errors.ObjectInUse:
            msg = "Error: Database cannot be rebuild " \
                 +"since it is currently in use.\n" \
                 +"Using existing database."
            print(msg)

        # run test suite
        print("Creating sample queries and output...")
        db.test_suite(user)
        print("Created sample queries and output.")

    elif (mode=="-i" or mode=="--interactive"):
        print("\n| Interactive-mode |\n")

        # run queries
        interactive_queries(user,db.name)


if (__name__ == "__main__"):
    main()
