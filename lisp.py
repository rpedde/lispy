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


def lisp_load(env, filename):
    with open(filename, 'r') as f:
        program = f.read()

    ast = Parser(program).ast
    return ast.eval(env)


class Environment(object):
    def __init__(self, prev=None, env={}):
        self.env = env
        self.prev = prev

    def get(self, symbol):
        logging.debug('Looking up symbol %s' % symbol)

        if not symbol in self.env:
            if self.prev is None:
                # or... return a symbol type... ?
                raise SyntaxError('Unknown symbol: %s' % symbol)
            else:
                logging.debug('Not found in env %s.  Upwarding to %s' % (id(self), id(self.prev)))
                return self.prev.get(symbol)

        return self.env[symbol]

    def set(self, symbol, value, with_create = False):
        logging.debug('setting symbol "%s"' % symbol)
        if not symbol in self.env and not with_create:
            if self.prev is None:
                raise SyntaxError('Unknown symbol: %s' % symbol)
            else:
                return self.prev.set(symbol, value, with_create)

        self.env[symbol] = value

    def flat_clone(self):
        reverse_list = []
        current = self
        while(current != None):
            reverse_list.insert(0, current)
            current = current.prev

        cloned_dict = {}
        for env in reverse_list:
            cloned_dict.update(copy.deepcopy(env.env))

        return Environment(prev=None, env=cloned_dict)

    def extend(self, extended_environment={}):
        return Environment(prev=self, env=extended_environment)


class Token(object):
    pass


class Function(object):
    pass


class LambdaFunction(Function):
    def __init__(self, env, formals, fn):
        self.name = 'lambda#%s' % id(self)
        self.formals = formals
        self.fn = fn
        self.env = env

    def __str__(self):
        return '%s(%s)' % (self.name, ' '.join(self.formals))

    def lispy_str(self):
        return '#fn#'

    def eval(self, env, *args):
        if len(args) != len(self.formals):
            raise SyntaxError('Function %s expects %d args, got %d' % (
                len(self.formals), len(args)))

        lambda_env = env.extend(self.env.env).extend(dict(zip(self.formals, [x.eval(env) for x in args])))
        return self.fn.eval(lambda_env)


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
                (test, if_true, if_false) = x[1:]
                result = if_true if test.eval(env).pyvalue(env) else if_false
                return result.eval(env)
            if x[0].name == 'quote':
                # should test arity
                return x[1]
            if x[0].name == 'define':
                logging.debug('defining %s' % x)
                (symbol, value) = x[1:]
                logging.debug('binding %s to %s' % (symbol.name, value.eval(env)))
                global_env.set(symbol.name, value.eval(env), with_create = True)
                return True
            if x[0].name == 'set!':
                (symbol, value) = x[1:]
                env.set(symbol.name, value.eval(env), with_create = False)
                return True
            if x[0].name == 'let':
                (pairslist, expr) = x[1:]
                new_env = env.extend()
                for pair in pairslist.pyvalue(env):
                    (key, value) = pair.pyvalue(env)
                    new_env.set(key.name, value.eval(env), with_create = True)
                return expr.eval(new_env)
            if x[0].name == 'let*':
                (pairslist, expr) = x[1:]
                new_env = env.extend()
                for pair in pairslist.pyvalue(env):
                    (key, value) = pair.pyvalue(env)
                    new_env.set(key.name, value.eval(new_env), with_create = True)
                return expr.eval(new_env)
            if x[0].name == 'lambda':
                (formals, expr) = x[1:]
                return LambdaFunction(env, [x.name for x in formals.value], expr)
            elif x[0].name == '':
                pass

        fn = x[0].eval(env)
        # if isinstance(x[0], Symbol):
        #     fn = x[0].eval(env)

        if not isinstance(fn, Function):
            raise SyntaxError('%s: %s is not a function' % (x[0], x[0].__class__.__name__))

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
        self.tokenlist = str.replace('(', ' ( ').replace(')', ' ) ').replace("'"," ' ").replace('\n','').split()
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

global_env = Environment(prev=None, env={
    '+': InternalFunction('+', lambda *x: reduce(operator.add, x[1:], x[0])),
    '-': InternalFunction('-', lambda *x: reduce(operator.sub, x[1:], x[0])),
    '*': InternalFunction('*', lambda *x: reduce(operator.mul, x[1:], x[0])),
    '/': InternalFunction('/', lambda *x: reduce(operator.div, x[1:], x[0])),
    'or': InternalFunction('or', lambda *x: reduce(operator.or_, x[1:], x[0])),
    'and': InternalFunction('and', lambda *x: reduce(operator.and_, x[1:], x[0])),
    'car': InternalFunction('car', lambda x: x[0], translate_return=False),
    'cdr': InternalFunction('cdr', lambda x: SExpr(x[1:]), translate_return=False),
    'list': InternalFunction('list', lambda *x: SExpr(list(x)), translate_types=False, translate_return=False),
    '>': InternalFunction('>', operator.gt),
    '<': InternalFunction('<', operator.lt),
    '>=': InternalFunction('>=', operator.ge),
    '<=': InternalFunction('<=', operator.le),
    '=': InternalFunction('=', operator.eq),
    'list?': InternalFunction('list?', lambda x: isinstance(x, SExpr), False),
    'symbol?': InternalFunction('symbol?', lambda x: isinstance(x, Symbol), False),
    'exit': InternalFunction('exit', lambda: sys.stdout.write("Bye!\n") or sys.exit(0)),
    'debug': InternalFunction('debug', set_loglevel),
    'eval': InternalFunction('eval', lisp_eval, False, False, True),
    'load': InternalFunction('load', lisp_load, translate_return=False, want_environment=True)
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

            result = ast.eval(global_env)
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

