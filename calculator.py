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
        while len(values) <= self.max_precount:
            token = tokens.get_token()
            if stop(token):
                tokens.push_token(token)
                if len(values) == valuecount:
                    return values
                raise ValueError('Missing expected value {}'.format(token))
            for argcount in range(len(values), -1, -1):
                if (token, argcount) in self.operators:
                    operator = self.operators[token, argcount]
                    break
                elif (Operator.ADJACENT, argcount) in self.operators:
                    operator = self.operators[Operator.ADJACENT, argcount]
                    break
            else:
                values.append(self._interpret(token)) # TODO!
                operator = None

            if operator:
                # Apply operator
                if operator.trump and operator.trump <= precedence: #outclassed
                    tokens.push_token(token)
                    return values #TODO!
                else:
                    values = [operator.calculate(self._eval, tokens, token, stop, *values)]

        raise ValueError('No operator takes {} values: {}'.format(len(values), values))


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

    @property
    def precount(self):
        return 1 if self.trump else 0

    def stop(self, token):
        if isinstance(self.precedence, str):
            return token == self.precedence
        else:
            return False

    def calculate(self, evaluate, tokens, token, stop, *values):
        if self.token is Operator.ADJACENT:
            tokens.push_token(token)
        values = list(values)
        if self.precedence is None: #Postfix
            pass
        elif isinstance(self.precedence, str): #group
            values.extend(evaluate(tokens, self.stop))
            end_token = tokens.get_token()
            if end_token != self.precedence:
                raise ValueError('Mismatched group: %s...%s' % (self.token, end_token))
        else:
            values.extend(evaluate(tokens, stop, self.precedence))
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
