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
        operators = list(operators or _default_operators)
        operators.append(Operator(None, self._interpret, None))
        self.operators = {(O.token, O.precount): O for O in operators}
        self.max_precount = max(O.precount for O in operators)
        self.tokenize = tokenize

    def __call__(self, expression):
        return self.calculate(expression)

    def calculate(self, tokens, stop='', precedence=0):
        try:
            get_token = tokens.get_token
        except AttributeError:
            tokens = self.tokenize(tokens)
            get_token = tokens.get_token
        values = list()
        while len(values) <= 1:
            token = get_token()
            if token == stop:
                break
            for argcount in range(len(values), -1, -1):
                if (token, argcount) in self.operators:
                    operator = self.operators[token, argcount]
                    break
                elif (None, argcount) in self.operators:
                    operator = self.operators[None, argcount]
                    break
            else:
                raise Exception
                #values.append(self._interpret(token)) # TODO!
                #continue

            # Apply operator
            if operator.trump < precedence: #outclassed
                break
            else:
                args = values[len(values)-operator.precount:]
                values = values[:len(values)-operator.precount] + [operator.process(self.calculate, tokens, token, stop, *args)]

        tokens.push_token(token)
        if len(values) == 1:
            return values[0]
        else:
            raise ValueError('No operator takes {} {} values: {}'.format(token, len(values), values))

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

    def __init__(self, *precedences):
        if isinstance(precedences[0], str) or precedences[0] is None:
            self.trump, self.precount, self.token = float("inf"), 0, precedences[0]
            self.precedences = precedences[1:-1]
        else:
            self.trump, self.token = precedences[:2]
            self.precount = 1
            self.precedences = precedences[2:-1]
        self.action = precedences[-1] or (lambda X: X)

    def process(self, evaluate, tokens, token, stop, *args):
        if self.token is None:
            tokens.push_token(token)
        args = list(args)
        for precedence in self.precedences:
            if isinstance(precedence, str): #group
                args.append(evaluate(tokens, precedence, 0))
                end_token = tokens.get_token()
                if end_token != precedence:
                    raise ValueError('Mismatched group: %s...%s != %s' % (self.token, end_token, precedence))
            elif callable(precedence):
                args.append(precedence(tokens.get_token()))
            else:
                args.append(evaluate(tokens, stop, precedence))
        return self.action(*args)


_default_operators = [
    Operator(510, '=', 500, lambda L,R: L.assign(R)),
    Operator(1090, '==', 1100, operator.eq),
    Operator(1090, '<=', 1100, operator.le),
    Operator(1090, '>=', 1100, operator.ge),
    Operator(1090, '!=', 1100, operator.ne),
    Operator(1090, '<', 1100, operator.lt),
    Operator(1090, '>', 1100, operator.gt),
    Operator(2090, '+', 2100, operator.add),
    Operator(2090, '-', 2100, operator.sub),
    Operator(2190, '*', 2200, operator.mul),
    Operator(2190, '/', 2200, operator.truediv),
    Operator(2310, '^', 2300, operator.pow),
    Operator(2390, None, 2400, _apply_or_mul),
    # Call-like
    Operator(3000, '[', ']', operator.getitem),
    # Postfix
    Operator(2295, '%', lambda x: x * 0.01),
    # Prefix
    Operator('+', 2305, operator.pos),
    Operator('-', 2305, operator.neg),
    # Grouping
    Operator('(', ')', None),
]


if __name__ == '__main__':
    import doctest
    doctest.testmod()
