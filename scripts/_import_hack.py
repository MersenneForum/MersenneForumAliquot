import sys
from os.path import realpath, join, dirname

def add_path_relative_to_script(p):
     sys.path.insert(0, realpath(join(dirname(sys.argv[0]), p)))
