"""Minimal S-expression reader/writer for KiCad files."""
class Sym(str):
    pass

def parse(text):
    pos = 0
    n = len(text)
    stack = [[]]
    while pos < n:
        c = text[pos]
        if c == '(':
            stack.append([]); pos += 1
        elif c == ')':
            l = stack.pop(); stack[-1].append(l); pos += 1
        elif c == '"':
            j = pos + 1; buf = []
            while text[j] != '"':
                if text[j] == '\\':
                    buf.append(text[j:j+2]); j += 2
                else:
                    buf.append(text[j]); j += 1
            stack[-1].append(''.join(buf)); pos = j + 1
        elif c.isspace():
            pos += 1
        else:
            j = pos
            while j < n and not text[j].isspace() and text[j] not in '()"':
                j += 1
            stack[-1].append(Sym(text[pos:j])); pos = j
    return stack[0][0]

def dump(x, ind=0):
    if isinstance(x, list):
        simple = all(not isinstance(e, list) for e in x)
        if simple:
            return '(' + ' '.join(dump(e) for e in x) + ')'
        out = '(' + dump(x[0])
        for e in x[1:]:
            if isinstance(e, list):
                out += '\n' + '\t' * (ind + 1) + dump(e, ind + 1)
            else:
                out += ' ' + dump(e)
        return out + '\n' + '\t' * ind + ')'
    if isinstance(x, Sym):
        return str(x)
    if isinstance(x, str):
        return '"' + x + '"'
    return str(x)

def find(node, key):
    return [e for e in node[1:] if isinstance(e, list) and e and e[0] == key]

def first(node, key):
    r = find(node, key)
    return r[0] if r else None
