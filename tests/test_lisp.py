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

    def t1080_test_eval_quote(self):
        assert(self.eval_expr('(eval (quote (+ 1 2)))') == 3)

    def t1090_test_quote_shortcut(self):
        assert(self.eval_expr("(eval '(+ 1 2))") == 3)

    def t1100_test_qq_shortcut(self):
        assert(self.eval_expr("(eval `(+ 1 2))") == 3)

    def t1110_test_qq_and_unquote(self):
        assert(self.eval_expr("(define x 3)(eval `(+ 1 ,x))") == 4)

    def t1120_test_qq_and_unquote_deep(self):
        assert(self.eval_expr("(define x 3)(eval `(+ 1 (+ 1 ,x)))") == 5)

    @raises(SyntaxError)
    def t1130_test_quote_arity(self):
        self.eval_expr('(quote 1 2 3)')

    @raises(SyntaxError)
    def t1140_test_unquote_outside_qq(self):
        self.eval_expr('(define x 3)(unquote x)')

    def t1150_test_unquote_splicing(self):
        assert(self.eval_expr("(define x '(1 2))(eval `(+ @x))") == 3)

    def t1160_test_unquote_splicing_deep(self):
        assert(self.eval_expr("(define x '(1 2))(eval `(+ 1 (+ @x)))") == 4)

    @raises(SyntaxError)
    def t1170_test_unquote_splicing_outside_qq(self):
        self.eval_expr("(define x '(1 2))(unquote-splicing x)")

    # test built-in functions
    def t2000_test_add_int(self):
        assert(self.eval_expr('(+ 1 2)') == 3)

    def t2010_test_add_arity(self):
        assert(self.eval_expr('(+ 1 1 1 1)') == 4)

    def t2020_test_sub_int(self):
        assert(self.eval_expr('(- 8 2)') == 6)

    def t2030_test_sub_arity(self):
        assert(self.eval_expr('(- 8 2 2)') == 4)

    def t2040_test_floatq(self):
        assert(self.eval_expr('(float? 1.1)'))

    def t2050_test_floatq(self):
        assert(self.eval_expr('(float? 1)') == False)

    def t2060_test_intq(self):
        assert(self.eval_expr('(int? 1)'))

    def t2070_test_intq(self):
        assert(self.eval_expr('(int? "hi")') == False)

    def t2080_test_stringq(self):
        assert(self.eval_expr('(string? "hi")'))

    def t2090_test_stringq(self):
        assert(self.eval_expr('(string? 1)') == False)

    def t2100_test_symbolq(self):
        assert(self.eval_expr('(symbol? (quote howdy))'))

    def t2110_test_symbolq(self):
        assert(self.eval_expr('(symbol? 1)') == False)

    def t2120_test_listq(self):
        assert(self.eval_expr('(list? (quote (1 2 3)))'))

    def t2130_test_listq(self):
        assert(self.eval_expr('(list? 1)') == False)

    def t2140_test_mult(self):
        assert(self.eval_expr('(* 1 2)') == 2)

    def t2150_test_mult_arity(self):
        assert(self.eval_expr('(* 2 2 2)') == 8)

    def t2160_test_div(self):
        assert(self.eval_expr('(/ 4 2)') == 2)

    def t2170_test_div_arity(self):
        assert(self.eval_expr('(/ 4 2 2)') == 1)

    def t2180_test_car(self):
        assert(self.eval_expr('(car (quote (1 2 3)))') == 1)

    def t2190_test_cdr(self):
        assert(self.eval_expr("(car (cdr '(1 2 3)))") == 2)

    
