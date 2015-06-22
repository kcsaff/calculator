"""
    >>> c = Calculator()
    >>> c('1+(1)')
    2
    >>> c('(((1))+(2))')
    3
    >>> c('2+3*4^2')
    50
    >>> c('2^2^2')
    16
    >>> c('---3')
    -3
    >>> c('-3^2')
    -9
    >>> round(c('-3^-2'), 6)
    -0.111111
    >>> c('---1 + 1')
    0
    >>> round(c('5%+7%'), 6)
    0.12
    >>> round(c('1%%%'), 6)
    1e-06
    >>> c('3(5)')
    15
    >>> c('2^3*4+5*6')
    62

    >>> values = dict(a=1, b=2, c=3)
    >>> d = Calculator((int, float, values.get))
    >>> d('a+b*c')
    7
    
    >>> import math
    >>> values['sqrt'] = math.sqrt
    >>> round(d('sqrt(4)'),6)
    2.0
    >>> round(d('sqrt 4 + 1'),6)
    3.0
    
    >>> values['hello'] = [1,2,3]
    >>> d('hello[-1]+1')
    4
"""
import operator
import shlex


class Calculator(object):
    def __init__(self, interpreters=None, operators=None, tokenize=shlex.shlex):
        self.interpreters = interpreters or _default_interpreters
        operators = operators or _default_operators
        self.operators = {(O.token, O.precount): O for O in operators}
        self.max_precount = max(O.precount for O in operators)
        self.tokenize = tokenize

    def calculate(self, expression):
        tokens = self.tokenize(expression)
        return self._eval(tokens)[0]

    def __call__(self, expression):
        return self.calculate(expression)

    def _interpret(self, token):
        for interpreter in self.interpreters:
            try:
                value = interpreter(token)
            except Exception as err:
                pass
            else:
                return value
        else:
            raise ValueError('Could not interpret %r' % token)

    def _eval(self, tokens, stop=(lambda X: not X), precedence=0, valuecount=1):
        values = list()
        while True:
            token = tokens.get_token()
            if stop(token):
                break
            for argcount in range(len(values), -1, -1):
                if (token, argcount) in self.operators:
                    operator = self.operators[token, argcount]
                    break
                elif (None, argcount) in self.operators:
                    operator = self.operators[None, argcount]
                    break
            else:
                values.append(self._interpret(token)) # TODO!
                continue

            # Apply operator
            if operator.trump < precedence: #outclassed
                break
            else:
                args = values[-argcount:]
                values = values[:-argcount] + [operator.calculate(self._eval, tokens, token, stop, *args)]

        tokens.push_token(token)
        if len(values) == valuecount:
            return values
        else:
            raise ValueError('No operator takes {} {} values: {}'.format(token, len(values), values))


def _apply_or_mul(left, right):
    try:
        return left(right)
    except Exception as err:
        return left * right

_default_interpreters = (
    int,
    float,
)


class Operator(object):
    ADJACENT = object()

    def __init__(self, *parts):
        if isinstance(parts[0], str):
            self.trump, self.precount, self.token = float("inf"), 0, parts[0]
            self.parts = parts[1:]
        else:
            self.trump, self.precount, self.token = parts[:3]
            self.parts = parts[3:]
        self.action = (lambda X: X)

    def __call__(self, action):
        self.action = action
        return self

    def calculate(self, evaluate, tokens, token, stop, *args):
        if self.token is None:
            tokens.push_token(token)
        args = list(args)
        for i in range(0, len(self.parts), 2):
            argcount = self.parts[i]
            precedence = self.parts[i+1] if len(self.parts) > i+1 else None
            if precedence is None: #Postfix
                pass
            elif isinstance(precedence, str): #group
                args.extend(evaluate(tokens, (lambda X: X == precedence), 0, argcount))
                end_token = tokens.get_token()
                if end_token != precedence:
                    raise ValueError('Mismatched group: %s...%s != %s' % (self.token, end_token, precedence))
            else:
                args.extend(evaluate(tokens, stop, precedence, argcount))
        return self.action(*args)


_default_operators = [
    Operator(510, 1, '=', 1, 500)(lambda L,R: L.assign(R)),
    Operator(1090, 1, '==', 1, 1100)(operator.eq),
    Operator(1090, 1, '<=', 1, 1100)(operator.le),
    Operator(1090, 1, '>=', 1, 1100)(operator.ge),
    Operator(1090, 1, '!=', 1, 1100)(operator.ne),
    Operator(1090, 1, '<', 1, 1100)(operator.lt),
    Operator(1090, 1, '>', 1, 1100)(operator.gt),
    Operator(2090, 1, '+', 1, 2100)(operator.add),
    Operator(2090, 1, '-', 1, 2100)(operator.sub),
    Operator(2190, 1, '*', 1, 2200)(operator.mul),
    Operator(2190, 1, '/', 1, 2200)(operator.truediv),
    Operator(2310, 1, '^', 1, 2300)(operator.pow),
    Operator(2390, 1, None, 1, 2400)(_apply_or_mul),
    # Call-like
    Operator(3000, 1, '[', 1, ']')(operator.getitem),
    # Postfix
    Operator(2295, 1, '%')(lambda x: x * 0.01),
    # Prefix
    Operator('+', 1, 2305)(operator.pos),
    Operator('-', 1, 2305)(operator.neg),
    # Grouping
    Operator('(', 1, ')'),
]


if __name__ == '__main__':
    import doctest
    doctest.testmod()
