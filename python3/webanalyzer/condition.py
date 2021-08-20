#! /usr/bin/env python
# -*- coding: utf-8 -*-

import string
import logging

__all__ = ["Condition", "ParseException"]

EOF = -1

TOKEN_TYPE = {
    'not': 'NOT',
    'and': 'AND',
    'or': 'OR',
    '(': 'LP',
    ')': 'RP',
    'variable': 'VARIABLE',
    'eof': 'EOF'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class ParseException(Exception):
    pass


class Token(object):
    def __init__(self, type: TOKEN_TYPE, name: str = '', value: bool = False):
        self.type = type
        self.name = name
        self.value = value

    def __str__(self):
        return '<Token {} {}>'.format(self.type, self.name)

    __repr__ = __str__


class Result(object):
    def __init__(self, name: str, value: bool):
        self.name = name
        self.value = value

    def __str__(self):
        return '<result {} = {}>'.format(self.name, self.value)

    __repr__ = __str__


class Condition(object):
    def __init__(self):
        self.condstr = ''
        self.index = 0
        self.back_tokens = []
        self.symbol_table = {}

        self.allow_character = string.ascii_lowercase + string.digits + '_'
        self.ignore_character = ' \t'

    def _get_token(self) -> Token:
        while self.index < len(self.condstr):
            if self.condstr[self.index] in self.ignore_character:
                self.index += 1
                continue

            if self.condstr[self.index: self.index + 2] == 'or' and \
                    self.condstr[self.index + 2] not in self.allow_character:
                name = self.condstr[self.index: self.index + 2]
                self.index += 2
                return Token(TOKEN_TYPE[name])

            elif self.condstr[self.index: self.index + 3] in ('not', 'and') and \
                    self.condstr[self.index + 3] not in self.allow_character:
                name = self.condstr[self.index: self.index + 3]
                self.index += 3
                return Token(TOKEN_TYPE[name])

            elif self.condstr[self.index] in ('(', ')'):
                name = self.condstr[self.index]
                self.index += 1
                return Token(TOKEN_TYPE[name])

            else:
                name = []
                while self.index < len(self.condstr) and self.condstr[self.index] in self.allow_character:
                    name.append(self.condstr[self.index])
                    self.index += 1

                name = ''.join(name)
                if name not in self.symbol_table:
                    raise ParseException('{} does not exists'.format(name))

                return Token(TOKEN_TYPE['variable'], name, self.symbol_table[name])

        return Token(TOKEN_TYPE['eof'])

    def pop_token(self) -> Token:
        if self.back_tokens:
            return self.back_tokens.pop(0)
        try:
            return self._get_token()
        except IndexError:
            raise ParseException('invalid condition "%s"', self.condstr)

    def push_token(self, token: Token):
        self.back_tokens.append(token)

    def parse_var_expression(self) -> Result:
        """
        v_exp := VARIABLE
        """
        token = self.pop_token()
        if token.type == TOKEN_TYPE['eof']:
            return Result(name='', value=False)

        if token.type != TOKEN_TYPE['variable']:
            raise ParseException('invalid condition "%s"' % self.condstr)

        return Result(name=token.name, value=token.value)

    def parse_primary_expression(self) -> Result:
        """
        p_exp := (exp)
        """
        token = self.pop_token()
        if token.type == TOKEN_TYPE['eof']:
            return Result(name='', value=False)
        elif token.type != TOKEN_TYPE['(']:
            self.push_token(token)
            return self.parse_var_expression()

        r = self.parse_expression()

        token = self.pop_token()
        if token.type != TOKEN_TYPE[')']:
            raise ParseException('invalid condition "%s"' % self.condstr)

        return r

    def parse_not_expression(self) -> Result:
        """
        n_exp := NOT n_exp | NOT p_exp
        """
        token = self.pop_token()
        if token.type == TOKEN_TYPE['eof']:
            return Result(name='', value=False)
        elif token.type != TOKEN_TYPE['not']:
            self.push_token(token)
            return self.parse_primary_expression()

        r1 = self.parse_not_expression()

        r = Result('(not {})'.format(r1.name), not r1.value)
        logger.debug('[*] {}'.format(r))
        return r

    def parse_and_expression(self) -> Result:
        """
        and_exp := and_exp AND n_exp
        """
        r1 = self.parse_not_expression()
        if not r1.name and not r1.value:
            return r1

        while True:
            token = self.pop_token()
            if token.type == TOKEN_TYPE['eof']:
                break

            if token.type != TOKEN_TYPE['and']:
                self.push_token(token)
                return r1

            r2 = self.parse_not_expression()
            if not r2.name and not r2.value:
                raise ParseException('invalid condition "%s"', self.condstr)

            r1 = Result('({} and {})'.format(r1.name, r2.name), r1.value and r2.value)
            logger.debug('[*] {}'.format(r1))

        return r1

    def parse_or_expression(self) -> Result:
        """
        or_exp := or_exp OR and_exp
        """
        r1 = self.parse_and_expression()
        if not r1.name and not r1.value:
            return r1

        while True:
            token = self.pop_token()
            if token.type == TOKEN_TYPE['eof']:
                break

            elif token.type != TOKEN_TYPE['or']:
                self.push_token(token)
                return r1

            r2 = self.parse_and_expression()
            if not r2.name and not r2.value:
                raise ParseException('invalid condition "%s"', self.condstr)

            r1 = Result('({} or {})'.format(r1.name, r2.name), r1.value or r2.value)
            logger.debug('[*] {}'.format(r1))

        return r1

    def parse_expression(self) -> Result:
        """
        exp := or_exp
        """
        return self.parse_or_expression()

    def parse(self, condstr: str, symbol_table: hash) -> bool:
        self.condstr = condstr.lower()
        self.symbol_table = symbol_table
        self.index = 0
        self.back_tokens = []

        result = self.parse_expression()

        if self.back_tokens:
            raise ParseException('invalid condition "%s"', self.condstr)

        return result.value


if __name__ == '__main__':
    s_tab = {
        "name1": True,
        "name2": False,
        "name3": True,
        "name4": False,
        "name100": False,
    }

    p = Condition()
    print(p.parse('not name2 and (name1 or name4)', s_tab))
