#!/usr/bin/env python

import sys
import copy
import operator
import readline
import logging
import traceback
import re
import getopt

import lisp

# testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR, format='%(message)s')
    exec_file = None
    exec_str = None
    print_python = False
    prog = None

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'e:f:p')
    except getopt.GetoptError as e:
        print '%s' % e
        sys.exit(1)

    for o, a in opts:
        if o == '-e':
            exec_str = a
        elif o == '-f':
            exec_file = a
        elif o == '-p':
            print_python = True
        else:
            print 'Bad option: %s' % o
            sys.exit(1)

    if exec_file is not None and exec_str is not None:
        print 'Cannot use both -e and -f options'
        sys.exit(1)

    if exec_str is not None:
        prog = lisp.Parser(exec_str)
    elif exec_file is not None:
        with open(exec_file, 'r') as f:
            prog = lisp.Parser(f.read())

    
    if prog is not None:
        while not prog.EOF():
            term = prog.read()
            result = term.eval(lisp.global_env)

        if result is not None:
            if print_python:
                result = result.pyvalue(lisp.global_env, deep=True)
            else:
                result = getattr(result, 'lispy_str', getattr(result, '__str__'))()

            print result
            sys.exit(0)

    readline.parse_and_bind('tab: complete')

    while True:
        try:
            line = raw_input("lispy> ")
        except EOFError:
            print "\nBye!"
            sys.exit(0)

        try:
            prog = lisp.Parser(line)
            logging.debug(prog.tokens)

            while not prog.EOF():
                term = prog.read()
                logging.debug(term)

                result = term.eval(lisp.global_env)
                if result is not None:
                    if getattr(result, 'lispy_str', None) is not None:
                        print result.lispy_str()
                    else:
                        print '%s' % result

        except SyntaxError as e:
            print 'Error: %s' % e
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print 'Internal Error: %s' % e
            for entry in traceback.extract_tb(exc_traceback):
                print 'Line %d: %s' % (entry[1], entry[3])

