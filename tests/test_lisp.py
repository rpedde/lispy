import os
import sys
import copy

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from lisp import Parser, generate_global_env

#from lisp import Parser, global_env, generate_global_env
from nose.tools import *

class TestLisp:
    def eval_expr(self, str, deep=True):
        prog = Parser(str)
        result = None

        env = generate_global_env()
        print env.env.keys()

        while not prog.EOF():
            term = prog.read()
            result = term.eval(env)

        print env.env.keys()
        return result.pyvalue(env, deep=deep)

    # test special forms
    def t1000_test_quote(self):
        assert(self.eval_expr('(quote (1 2 3))') == [1, 2, 3])

    def t1010_test_lt(self):
        assert(self.eval_expr('(< 1 2)') == True)

    def t1011_test_lt(self):
        assert(self.eval_expr('(< 2 1)') == False)

    def t1020_test_if(self):
        assert(self.eval_expr('(if (< 1 2) 1 2)') == 1)

    def t1021_test_if(self):
        assert(self.eval_expr('(if (< 2 1) 1 2)') == 2)

    def t1030_test_define(self):
        assert(self.eval_expr('(define x 1) x') == 1)

    @raises(SyntaxError)
    def t1031_test_define_not_top_level(self):
        self.eval_expr('((lambda () (define x 1)))')

    @raises(SyntaxError)
    def t1040_test_unbound(self):
        self.eval_expr('x')

    @raises(SyntaxError)
    def t1050_test_syntax_error(self):
        # not a function
        self.eval_expr('(define x 1)(x 1 2)')

    def t1060_test_lambda(self):
        assert(self.eval_expr('((lambda (x) x) 1)') == 1)

    def t1060_test_let(self):
        assert(self.eval_expr('(let ((x 1)) ((lambda () x)))') == 1)

    def t1070_test_let_shadows_globals(self):
        assert(self.eval_expr('(define x 1)(let ((x 2)) ((lambda () x)))') == 2)

    # test built-in functions
    def t2000_test_add_int(self):
        assert(self.eval_expr('(+ 1 2)') == 3)

    def t2000_test_add_arity(self):
        assert(self.eval_expr('(+ 1 1 1 1)') == 4)


    