#!/usr/bin/env python

import copy
import operator
import readline
import sys
import logging
import traceback
import re

DEBUG=False

def set_loglevel(level):
    if not isinstance(level, basestring) or \
       level.upper() not in ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']:
        raise SyntaxError('log level must be CRITICAL, ERROR, WARNING, INFO, or DEBUG')

    logging.getLogger().setLevel(getattr(logging, level.upper()))
    return 0


def lisp_eval(env, arg):
    return arg.eval(env)


def lisp_quasiquote(env, expr):
    # recursively parse the expr as a quoted expression, but dequoting (by eval)
    # "unquote"-ed and "unquote-splicing"-ed terms
    if isinstance(expr, SExpr):
        if isinstance(expr.value[0], Symbol) and expr.value[0].name == 'unquote':
            return expr.value[1].eval(env)
        elif isinstance(expr.value[0], Symbol) and expr.value[0].name == 'unquote-splicing':
            result = expr.value[1].eval(env)
            if not isinstance(result, SExpr):
                raise SyntaxError('unquote-splicing result is not a list')
            return result.value
        else:
            result = []
            for x in expr.value:
                qq = lisp_quasiquote(env, x)
                if isinstance(qq, list):
                    result = result + qq
                else:
                    result.append(qq)
            return SExpr(result)
    else:
        return expr

def lisp_unquote(env, *expr):
    raise SyntaxError("unquote invalid outside quasiquote")

def lisp_load(env, filename):
    try:
        with open(filename, 'r') as f:
            program = f.read()
    except:
        raise SyntaxError('File open error on %s' % filename)

    parser = Parser(program)
    while not parser.EOF():
        term = parser.read()
        try:
            term.eval(env)
        except Exception as e:
            raise SyntaxError('Eval error: %s' % e)
    return None


def lisp_format(env, format, *args):
    split = format.split('~A')
    result = split[0]
    split.pop(0)
    args = list(args)
    while(len(split)):
        result += str(args[0])
        args.pop(0)
        result += split[0]
        split.pop(0)
    return result


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
                result = self.prev.get(symbol)
                logging.debug('Upwardly resolved %s to %s' % (symbol, result))
                return result

        result = self.env[symbol]
        logging.debug('Directly resolved %s to %s' % (symbol, result))
        return result

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

    def pyvalue(self, env, deep=False):
        if deep:
            return [x.pyvalue(env, True) for x in self.value]

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
                if len(x) != 2:
                    raise SyntaxError('wrong arity for "quote"')
                return x[1]
            if x[0].name == 'quasiquote':
                if len(x) != 2:
                    raise SyntaxError('wrong arity for "quasiquote"')
                result = lisp_quasiquote(env, x[1])
                if isinstance(result, list):
                    return SExpr(result)
                return result
            if x[0].name == 'define':
                logging.debug('defining %s' % x)
                (symbol, value) = x[1:]
                logging.debug('binding %s to %s' % (symbol.name, value.eval(env)))
                if env.prev is not None:
                    raise SyntaxError('Can only define at top level')
                env.set(symbol.name, value.eval(env), with_create = True)
                return None
            if x[0].name == 'set!':
                (symbol, value) = x[1:]
                env.set(symbol.name, value.eval(env), with_create = False)
                return None
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
            if x[0].name == 'begin':
                for expr in x[1:]:
                    result = expr.eval(env)
                return result
            if x[0].name == 'lambda':
                (formals, expr) = x[1:]
                return LambdaFunction(env, [x.name for x in formals.value], expr)

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

    def pyvalue(self, env, deep=False):
        lispvalue = self.eval(env)

        if isinstance(lispvalue, Function):
            raise SyntaxError("Sorry Dave.  I can't pass functions to python functions")

        return lispvalue.pyvalue(env)

    def eval(self, env):
        return env.get(self.name)


class Constant(Token):
    def __init__(self, value):
        self.value = value

    def lispy_str(self):
        return "%s" % self.value

    def pyvalue(self, env, deep=False):
        return self.value

    def eval(self, env):
        return self


class ConstantString(Constant):
    def __repr__(self):
        return 'String: "%s"' % self.value


class ConstantInt(Constant):
    def __repr__(self):
        return 'Int: %d' % self.value


class ConstantFloat(Constant):
    def __repr__(self):
        return 'Float: %f' % self.value


class Parser(object):
    def __init__(self, str):
        self.scanner = re.Scanner([
            (r'[0-9]+\.[0-9]+', self.float_type),
            (r'[0-9]+', self.int_type),
            (r'[ \t\n]+', None),
            (r'"([^"\\]*(?:\\.[^"\\]*)*)"', self.string_type),
            (r'\(', self.baretoken),
            (r'\)', self.baretoken),
            (r'\'', self.baretoken),  # quote
            (r',', self.baretoken),   # unquote
            (r'`', self.baretoken),   # quasiquote
            (r'@', self.baretoken),   # unquote-splicing
            (r'[^ \t\n\(\)\'`@,]+', self.symbol_type)
        ])
        
        self.tokens, self.remainder = self.tokenize(str)

    # token building helpers
    def int_type(self, scanner, token):
        return 'CONST', ConstantInt(int(token))

    def float_type(self, scanner, token):
        return 'CONST', ConstantFloat(float(token))
        
    def string_type(self, scanner, token):
        return 'CONST', ConstantString(token[1:-1].replace('\\"', '"').replace('\\n', '\n'))

    def baretoken(self, scanner, token):
        return token, token

    def symbol_type(self, scanner, token):
        return 'SYMBOL', Symbol(token)
        
    def tokenize(self, str):
        tokens, remainder = self.scanner.scan(str)
        tokens.append(('EOF', None))
        return tokens, remainder

    def peek(self):
        return self.tokens[0]

    def scan(self):
        if self.tokens[0][0] == 'EOF':
            raise SyntaxError('Premature end of line.  (Missing paren?)')

        return self.tokens.pop(0)
        
    def EOF(self):
        return self.peek()[0] == 'EOF'

    def read(self):
        token, val = self.scan()
        if token in ",`'@":
            val = SExpr([{"'": Symbol('quote'),
                          '`': Symbol('quasiquote'),
                          ',': Symbol('unquote'),
                          '@': Symbol('unquote-splicing')}[token],
                         self.read() ])
        elif token == '(':
            ary = []
            while self.peek()[0] != ')':
                ary.append(self.read())
            self.scan()
            val = SExpr(ary)
        return val


def generate_global_env():
    return Environment(prev=None, env={
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
        'int?': InternalFunction('int?', lambda x: isinstance(x, ConstantInt), False),
        'string?': InternalFunction('string?', lambda x: isinstance(x, ConstantString), False),
        'float?': InternalFunction('float?', lambda x: isinstance(x, ConstantFloat), False),
        'exit': InternalFunction('exit', lambda: sys.stdout.write('Bye!\n') or sys.exit(0)),
        'debug': InternalFunction('debug', set_loglevel),
        'eval': InternalFunction('eval', lisp_eval, False, False, True),
        'load': InternalFunction('load', lisp_load, translate_return=False, want_environment=True),
        'print': InternalFunction('print', lambda x: sys.stdout.write('%s' % x), translate_return=False),
        'format': InternalFunction('format', lisp_format, translate_types=True, translate_return=True, want_environment=True),
        # 'quasiquote': InternalFunction('quasiquote', lisp_quasiquote, translate_types=False, translate_return=False, want_environment=True),
        'unquote': InternalFunction('unquote', lisp_unquote)
})

global_env = generate_global_env()

