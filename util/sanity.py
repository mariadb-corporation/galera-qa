#!/usr/bin/env python3
import os
import sys
from datetime import datetime


def check_python_version():
    """ Check python version. Raise error if the
        version is 3.7 or greater
    """
    if sys.version_info < (3, 7):
        print("\nError! You should use python 3.7 or greater\n")
        exit(1)


def version_check(basedir):
    # Get database version number
    version_info = os.popen(basedir + "/bin/mysqld --version 2>&1 "
                                      "| grep -oe '[0-9]\.[0-9][\.0-9]*' | head -n1").read()
    version = "{:02d}{:02d}{:02d}".format(int(version_info.split('.')[0]),
                                          int(version_info.split('.')[1]),
                                          int(version_info.split('.')[2]))
    return version


