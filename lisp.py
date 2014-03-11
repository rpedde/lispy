#!/usr/bin/env python

import copy
import operator

class Environment(object):
    def __init__(self, env={}):
        self.env = env

    def get(self, symbol):
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
    def __init__(self, fn, translate_types=True):
        self.fn = fn;
        self.translate = translate_types

    def eval(self, env, *args):
        real_args = args

        if self.translate:
            real_args = []
            for arg in args:
                if isinstance(arg, SExpr):
                    real_args.append(arg.eval(env).eval(env))
                else:
                    real_args.append(arg.eval(env))

        print 'Evaling function %s with args %s' % (self.fn, real_args)
        retval = Constant(self.fn(*real_args))
        print 'Result: %s' % retval
        return retval


class SExpr(Token):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return 'Sexpr: %s' % self.value

    def eval(self, env):
        fn = None

        x = self.value

        if isinstance(x[0], Symbol):
            if x[0].name == 'if':
                (_, test, if_true, if_false) = x
                result = if_true if test.eval(env) else if_false
                return result.eval(env)
            elif x[0].name == '':
                pass

        if isinstance(x[0], Symbol):
            fn = x[0].eval(env)

        if not isinstance(fn, Function):
            raise SyntaxError('Not a function')

        return fn.eval(env, *self.value[1:])
        

class Symbol(Token):
    def __init__(self, name):
        self.name = name
        
    def eval(self, env):
        return env.get(self.name)

    def __repr__(self):
        return 'Sym: "%s"' % self.name


class Constant(Token):
    def __init__(self, value):
        self.value = value

    def eval(self, env):
        return self.value

    def __repr__(self):
        return 'Const: "%s"' % self.value


class Parser(object):
    def __init__(self, str):
        self.tokenlist = str.replace('(', ' ( ').replace(')', ' ) ').split()
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
        if token != '(':
            raise SyntaxError('Expecting (')

        ast = SExpr(self.read_list())

        if not self.EOF():
            raise SyntaxError('Unexpect data beyond EOF')

        return ast

    def read_list(self):
        result = []
        token = self.next()
        while(token != ')'):
            if(token == '('):
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
    '+': InternalFunction(lambda *x: reduce(operator.add, x, 0)),
    '-': InternalFunction(lambda *x: reduce(operator.sub, x[1:], x[0])),
    '*': InternalFunction(lambda *x: reduce(operator.mul, x, 1)),
    '/': InternalFunction(lambda *x: reduce(operator.div, x[1:], x[0])),
    'car': InternalFunction(lambda x: x[0]),
    'cdr': InternalFunction(lambda x: x[1:]),
    'list': InternalFunction(lambda *x: SExpr(list(x))),
    '>': InternalFunction(operator.gt),
    '<': InternalFunction(operator.lt),
    '>=': InternalFunction(operator.ge),
    '<=': InternalFunction(operator.le),
    '=': InternalFunction(operator.eq),
    'list?': InternalFunction(lambda x: isinstance(x, SExpr)),
    'symbol?': InternalFunction(lambda x: isinstance(x, Symbol)),
    'quote': InternalFunction(lambda x: Constant(x), False)
})


# testing
if __name__ == "__main__":
    program = "(quote (1 2 3))"
    ast = Parser(program).ast
    print ast
    print ast.eval(init_env)

