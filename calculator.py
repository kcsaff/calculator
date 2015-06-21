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
        self.operators = {O.token: O for O in operators if not O.is_prefix()}
        self.groups = {O.token: O for O in operators if O.is_prefix()}
        self.tokenize = tokenize

    def calculate(self, expression):
        tokens = self.tokenize(expression)
        return self._eval(tokens)

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

    def _eval(self, tokens, stop=(lambda X: not X), precedence=0):
        # Value
        token = tokens.get_token()
        if stop(token):
            raise ValueError('Missing expected value')
        elif token in self.groups: #prefix or group
            value = self.groups[token].calculate(self._eval, tokens, stop)
        else:
            value = self._interpret(token)

        # Operators
        while True:

            # Figure operator
            token = tokens.get_token()
            if stop(token):
                tokens.push_token(token)
                return value
            elif token in self.operators:
                operator = self.operators[token]
            elif Operator.ADJACENT in self.operators:
                operator = self.operators[Operator.ADJACENT]
                tokens.push_token(token)
            else:
                raise ValueError('Missing expected operator')

            # Apply operator
            if operator.trump <= precedence: #outclassed
                if operator.token is not Operator.ADJACENT:
                    tokens.push_token(token)
                return value
            elif operator.precedence is not None: #infix
                value = operator.calculate(self._eval, tokens, stop, value)
            else: #postfix
                value = operator.action(value)


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

    def __init__(self, token, action, precedence, trump=None):
        self.token = token
        self.action = action
        self.precedence = precedence
        self.trump = trump

    def is_prefix(self):
        return self.trump is None

    def stop(self, token):
        if isinstance(self.precedence, str):
            return token == self.precedence
        else:
            return False

    def calculate(self, evaluate, tokens, stop, *values):
        values = list(values)
        if self.precedence is None: #Postfix
            pass
        if isinstance(self.precedence, str): #group
            values.append(evaluate(tokens, self.stop))
            end_token = tokens.get_token()
            if end_token != self.precedence:
                raise ValueError('Mismatched group: %s...%s' % (self.token, end_token))
        else:
            values.append(evaluate(tokens, stop, self.precedence))
        return self.action(*values)


_default_operators = [
    Operator('=', (lambda L,R: L.assign(R)), 500, 510),
    Operator('==', operator.eq, 1100, 1090),
    Operator('<=', operator.le, 1100, 1090),
    Operator('>=', operator.ge, 1100, 1090),
    Operator('!=', operator.ne, 1100, 1090),
    Operator('<', operator.lt, 1100, 1090),
    Operator('>', operator.gt, 1100, 1090),
    Operator('+', operator.add, 2100, 2090),
    Operator('-', operator.sub, 2100, 2090),
    Operator('*', operator.mul, 2200, 2190),
    Operator('/', operator.truediv, 2200, 2190),
    Operator('^', operator.pow, 2300, 2310),
    Operator(Operator.ADJACENT, _apply_or_mul, 2400, 2390),
    # Call-like
    Operator('[', operator.getitem, ']', 3000),
    # Postfix
    Operator('%', (lambda x: x * 0.01), None, 2295),
    # Prefix
    Operator('+', operator.pos, 2305, None),
    Operator('-', operator.neg, 2305, None),
    # Grouping
    Operator('(', (lambda x: x), ')', None),
]


if __name__ == '__main__':
    import doctest
    doctest.testmod()
