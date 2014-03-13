#!/usr/bin/env python

import copy
import operator
import readline
import sys
import logging
import traceback

DEBUG=False

def set_loglevel(level):
    if not isinstance(level, basestring) or \
       level.upper() not in ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']:
        raise SyntaxError('log level must be CRITICAL, ERROR, WARNING, INFO, or DEBUG')

    logging.getLogger().setLevel(getattr(logging, level.upper()))
    return 0

def lisp_eval(env, arg):
    return arg.eval(env)

class Environment(object):
    def __init__(self, env={}):
        self.env = env

    def get(self, symbol):
        logging.debug('looking up symbol "%s"' % symbol)

        if symbol in self.env:
            return self.env[symbol]

        # what to do?
        raise SyntaxError('Unknown symbol: %s' % symbol)

    def set(self, symbol, value):
        env[symbol] = value

    def unset(self, symbol):
        del env[symbol]

    def extend(self, extended_environment):
        new_env = copy.deepcopy(self.env)
        new_env.update(extended_environment)
        return Environment(new_env)


class Token(object):
    pass


class Function(object):
    pass


class InternalFunction(Function):
    def __init__(self, name, fn, translate_types=True, translate_return=True, want_environment=False):
        self.name = name
        self.fn = fn;
        self.translate = translate_types
        self.translate_return = translate_return
        self.env = want_environment

    def __repr__(self):
        return 'Fn: %s' % self.name

    def lispy_str(self):
        return self.name

    def eval(self, env, *args):
        real_args = [arg.eval(env) for arg in args]

        if self.translate:
            real_args = [arg.pyvalue(env) for arg in real_args]

        logging.info('Evaling function "%s" with args %s' % (self.name, real_args))
        
        if self.env:
            real_args.insert(0, env)

        retval = self.fn(*real_args)

        logging.info('Result: %s' % retval)
        if self.translate_return:
            retval = Constant(retval)
            
        return retval

class SExpr(Token):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return 'Sexpr: %s' % self.value

    def lispy_str(self):
        return '(%s)' % ' '.join([x.lispy_str() for x in self.value])

    def pyvalue(self, env):
        return self.value
        
    def eval(self, env):
        fn = None

        x = self.value

        if isinstance(x[0], Symbol):
            if x[0].name == 'if':
                (_, test, if_true, if_false) = x
                result = if_true if test.eval(env) else if_false
                return result.eval(env)
            if x[0].name == 'quote':
                # should test arity
                return x[1]
            elif x[0].name == '':
                pass

        if isinstance(x[0], Symbol):
            fn = x[0].eval(env)

        if not isinstance(fn, Function):
            raise SyntaxError('%s: Not a function' % x[0])

        return fn.eval(env, *self.value[1:])
        

class Symbol(Token):
    def __init__(self, name):
        self.name = name
        
    def __repr__(self):
        return 'Sym: "%s"' % self.name

    def lispy_str(self):
        return self.name

    def pyvalue(self, env):
        lispvalue = self.eval(env)

        if isinstance(lispvalue, Function):
            raise SyntaxError("Sorry Dave.  I can't pass functions to python functions")

        return lispvalue.pyvalue(env)

    def eval(self, env):
        return env.get(self.name)


class Constant(Token):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return 'Const: "%r"' % self.value

    def lispy_str(self):
        return '%s' % self.value

    def pyvalue(self, env):
        # if isinstance(self.value, Token):
        #     return self.value.pyvalue(env)

        return self.value

    def eval(self, env):
        return self


class Parser(object):
    def __init__(self, str):
        self.tokenlist = str.replace('(', ' ( ').replace(')', ' ) ').replace("'"," ' ").split()
        self.index=0
        self.ast = self.astize()
        
    def next(self):
        if self.index + 1 > len(self.tokenlist):
            raise SyntaxError('Unexpected data beyond end of program')

        result, self.index = self.tokenlist[self.index], self.index + 1
        return result
    
    def EOF(self):
        return (self.index + 1 > len(self.tokenlist))

    def astize(self):
        token = self.next()
        if token == '(':
            ast = SExpr(self.read_list())
        else:
            ast = self.wrap_token(token)

        if not self.EOF():
            raise SyntaxError('Unexpect data beyond EOF')

        return ast

    def read_list(self):
        result = []
        token = self.next()

        while(token != ')'):
            if token == "'":
                new_sexpr = [ Symbol('quote') ]
    
                token = self.next()
                if token == '(':
                    new_sexpr.append(SExpr(self.read_list()))
                else:
                    new_sexpr.append(self.wrap_token(token))
                result.append(SExpr(new_sexpr))

            elif(token == '('):
                result.append(SExpr(self.read_list()))
            else:
                result.append(self.wrap_token(token))
            token = self.next()
        return result

    def wrap_token(self, token):
        try:
            return Constant(int(token))
        except ValueError:
            pass

        try:
            return Constant(float(token))
        except ValueError:
            pass

        if token.startswith('"') and token.endswith('"'):
            return Constant(token[1:-1])

        return Symbol(token)

init_env = Environment({
    '+': InternalFunction('+', lambda *x: reduce(operator.add, x, 0)),
    '-': InternalFunction('-', lambda *x: reduce(operator.sub, x[1:], x[0])),
    '*': InternalFunction('*', lambda *x: reduce(operator.mul, x, 1)),
    '/': InternalFunction('/', lambda *x: reduce(operator.div, x[1:], x[0])),
    'car': InternalFunction('car', lambda x: x[0], translate_return=False),
    'cdr': InternalFunction('cdr', lambda x: SExpr(x[1:]), translate_return=False),
    'list': InternalFunction('list', lambda *x: SExpr(list(x)), False),
    '>': InternalFunction('>', operator.gt),
    '<': InternalFunction('<', operator.lt),
    '>=': InternalFunction('>=', operator.ge),
    '<=': InternalFunction('<=', operator.le),
    '=': InternalFunction('=', operator.eq),
    'list?': InternalFunction('list?', lambda x: isinstance(x, SExpr), False),
    'symbol?': InternalFunction('symbol?', lambda x: isinstance(x, Symbol), False),
    'exit': InternalFunction('exit', lambda: sys.stdout.write("Bye!\n") or sys.exit(0)),
    'debug': InternalFunction('debug', set_loglevel),
    'eval': InternalFunction('eval', lisp_eval, False, False, True)
})


# testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR, format='%(message)s')
    readline.parse_and_bind('tab: complete')

    while True:
        try:
            line = raw_input("lispy> ")
        except EOFError:
            print "\nBye!"
            sys.exit(0)

        try:
            ast = Parser(line).ast
            logging.debug(ast)
            print ast.eval(init_env).lispy_str()
        except SyntaxError as e:
            print 'Error: %s' % e
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print 'Internal Error: %s' % e
            for entry in traceback.extract_tb(exc_traceback):
                print 'Line %d: %s' % (entry[1], entry[3])

