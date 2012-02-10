
"""
Implementation of the command-line I{pyflakes} tool.
"""

import sys
import os
import _ast
import optparse

checker = __import__('pyflakes.checker').checker

def check(codeString, filename, options):
    """
    Check the Python source given by C{codeString} for flakes.

    @param codeString: The Python source to check.
    @type codeString: C{str}

    @param filename: The name of the file the source came from, used to report
        errors.
    @type filename: C{str}
    @type options: object from optparse

    @return: The number of warnings emitted.
    @rtype: C{int}
    """
    # First, compile into an AST and handle syntax errors.
    try:
        tree = compile(codeString, filename, "exec", _ast.PyCF_ONLY_AST)
    except SyntaxError, value:
        msg = value.args[0]

        (lineno, offset, text) = value.lineno, value.offset, value.text

        # If there's an encoding problem with the file, the text is None.
        if text is None:
            # Avoid using msg, since for the only known case, it contains a
            # bogus message that claims the encoding the file declared was
            # unknown.
            print >> sys.stderr, "%s: problem decoding source" % (filename, )
        else:
            line = text.splitlines()[-1]

            if offset is not None:
                offset = offset - (len(text) - len(line))

            print >> sys.stderr, '%s:%d: %s' % (filename, lineno, msg)
            print >> sys.stderr, line

            if offset is not None:
                print >> sys.stderr, " " * offset, "^"

        return 1
    else:
        # Okay, it's syntactically valid.  Now check it.
        w = checker.Checker(tree, filename)
        w.messages.sort(lambda a, b: cmp(a.lineno, b.lineno))
        warnings = 0
        for warning in w.messages:
            if skip_warning(warning, options.ignore_messages if options else []):
                continue
            if options and not options.quiet:
                print warning
            warnings += 1
        if options and options.quiet:
            if warnings:
                sys.stdout.write('F')
            else:
                sys.stdout.write('.')
            sys.stdout.flush()
        return warnings

def memoize_lines(fn):
    data = {}
    def memo(filename):
        if filename not in data:
            data[filename] = fn(filename)
        return data[filename]
    return memo

@memoize_lines
def source_lines(filename):
    return open(filename).readlines()

def skip_warning(warning, ignore_messages):
    if ignore_messages:
        # these are post-substitued messages that are asked to be skipped
        message = warning.message % warning.message_args
        if message in ignore_messages:
            return True
    
    # quick dirty hack, just need to keep the line in the warning
    line = source_lines(warning.filename)[warning.lineno-1]
    return skip_line(line)

def skip_line(line):
    return line.rstrip().endswith('# pyflakes.ignore')

def checkPath(filename, options=None):
    """
    Check the given path, printing out any warnings detected.

    @return: the number of warnings printed
    """
    try:
        return check(file(filename, 'U').read() + '\n', filename, options)
    except IOError, msg:
        print >> sys.stderr, "%s: %s" % (filename, msg.args[1])
        return 1


def main():
    parser = optparse.OptionParser(usage='usage: %prog [options] module')
    parser.add_option('-q', '--quiet', action='store_true', dest='quiet', help='run in a quiet mode', default=False)
    parser.add_option('-i', '--ignore', action='append', dest='ignore_messages', help='specific messages to ignore', default=[])
    
    (options, args) = parser.parse_args()
    warnings = 0
    if not args:
        args = ['.']
    if '<stdin>' in args:
        warnings += check(sys.stdin.read(), '<stdin>', options)
    else:
        for arg in args:
            if os.path.isdir(arg):
                for dirpath, dirnames, filenames in os.walk(arg):
                    for filename in filenames:
                        if filename.endswith('.py'):
                            warnings += checkPath(os.path.join(dirpath, filename), options)
            else:
                warnings += checkPath(arg, options)
    if options.quiet:
        sys.stdout.write("\n")
    raise SystemExit(warnings > 0)
