#!/usr/bin/env python3
"""
Produce daily readable Log files:
*locally in the calling users home-directory
*globally in /home if called by root/sudo

Classes:

    LogFile
    CronJob
    User
"""

from datetime import date
import re
import subprocess


class LogFile:
    """
    A class to represent a Log file.

    ...

    Instance Attributes
    -------------------
    _name : str
        name of the Log file
    _location : str
        path to the Log file

    Instance Methods
    ----------------
    copy_log(destination):
        Copies Log to destination.
    _read_log():
        Reads from Log file, one line at a time.
    _write_log():
        Writes trimmed Log to file YYYY-MM-dd, one line at a time.
    trim_log():
        Trims Log to improve readability.
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


    def _write_log(self):
        """Writes trimmed Log to file YYYY-MM-dd, one line at a time."""

        fname = f"{self._location}/"+date.today().strftime("%Y-%m-%d")
        try:
            with open(fname,"w") as logfile:
                while True:
                    data = (yield)
                    logfile.write(data+"\n")
        except PermissionError:
            msg = f"You lack permission to create {fname}."
            print(msg)


    def trim_log(self):
        """
        Trims Log to improve readability.
        
        Modify whitelist to control filter.
        """

        # whitelist of filter
        whitelist = [" EMERGENCY:"," ALERT:"," CRITICAL:"," ERROR:",\
                     " WARNING:"," NOTICE:"," INFORMATIONAL:"," DEBUG:"]
    
        write_gen = self._write_log()
        write_gen.send(None)
    
        for line_log in self._read_log():
            # check if line contains whitelist entry
            is_allowed = [(wl_entry in line_log) for wl_entry in whitelist]
            if (any(is_allowed)):
                wl_entry = whitelist[is_allowed.index(True)]
            else:
                # omit lines without whitelist entry
                continue
    
            # keep timestamp, messages with whitelist entry
            time_pattern = r"^(.+?)\s"
            wl_pattern = r"("+wl_entry+r".+?)$"
            timestamp = re.search(time_pattern,line_log).group(1)
            wl_message = re.search(wl_pattern,line_log).group(1).strip()
            line_mod = " - ".join([timestamp,wl_message])
    
            write_gen.send(line_mod)
    
        # close generator
        write_gen.close()


class CronJob:
    """
    A class to represent a cronjob.

    ...

    Instance Attributes
    -------------------
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

    Instance Methods
    ----------------
    add_cronjob():
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


    def add_cronjob(self):
        """Adds cronjob to crontab."""

        print("Create a cronjob to execute this script "+ \
              "daily on working days.\n")
        input("Press Enter to modify the exemplary cronjob "+ \
              "on the last line... ")

        # add cronjob to crontab
        job = f"{self._m}\t{self._h}\t"+ \
              f"{self._dom}\t{self._mon}\t{self._dow}\t"+ \
              f"{self._exe} {self._file}"
        cmd = f"(crontab -l; echo \"{job}\") | crontab -"
        subprocess.call(cmd,shell=True)
        # allow for modification of cronjob or approval
        cmd = "crontab -e"
        subprocess.call(cmd,shell=True)


class User:
    """
    A class to represent the user.

    ...

    Instance Attributes
    -------------------
    _name : str
        name of the user
    home : str
        home-directory of the user

    Class Methods
    -------------
    grant_permissions():
        Grant permissions for files.
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


    @staticmethod
    def grant_permissions(files,permissions):
        """Grant permissions for files."""

        num_files = len(files)
        if (num_files == len(permissions)):
            for ii in range(num_files):
                cmd = f"chmod {permissions[ii]} {files[ii]}"
                subprocess.call(cmd,shell=True)
        else:
            raise Assertion.Error("Number of files and "+ \
                                  "permissions do not match.")


def main():
    """
    Sets up cronjob, copies system Log file,
    produces modified Log file and grants 
    permissions.
    """

    print("\n| ReadAble Logs |\n")

    cronjob = CronJob("0","0","*","*","1-5","python3",f"{__file__}")
    if (not cronjob.active):
        cronjob.add_cronjob()

    log_file = LogFile("syslog","/var/log")
    user = User()
    log_file.copy_log(user.home)
    log_file.trim_log()

    file_list = [f"{user.home}/syslog"]
    perm_list = ["o+r"]
    user.grant_permissions(file_list,perm_list)


if (__name__ == "__main__"):
    main()
