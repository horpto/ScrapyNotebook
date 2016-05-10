#!/bin/env python
# -*- encoding: utf-8 -*-

import inspect

SRC_LABEL_ATTR = '_rpyc_source_code'

def create_function(src):
    env, code = {}, compile(src, '<input>', 'exec')
    eval(code, env) # DANGEROUS, not safety
    env.pop('__builtins__')
    keys = env.keys()
    if len(keys) != 1:
        raise ValueError("Should be only one function, but there is %s" % keys)
    return env[keys[0]]

def mark_source_method(obj, method_name, src):
    if not isinstance(obj, type):
        obj = type(obj)
    func = create_function(src)
    setattr(func, SRC_LABEL_ATTR, src)
    return func


def get_source(obj):
    src = getattr(obj, SRC_LABEL_ATTR, None)
    if src:
        return src

    attr = {name: getattr(obj, name) for name in dir(obj)}
    ischanged = any(getattr(val, SRC_LABEL_ATTR, False)
                    for val in attr.itervalues())
    if (inspect.isroutine(obj) or not ischanged):
        try:
            source = inspect.getsource(obj)
            return cut_excess(source)
        except TypeError:
            pass
        try:
            source = inspect.getsource(type(obj))
            return cut_excess(source)
        except:
            # Ok, cannot get source.
            # For example, it's class created in IPython
            # Let's try to collect from methods.
            pass
    if inspect.ismodule(obj):
        return join_functions(obj, attr)
    if inspect.isclass(obj):
        return get_source_class(obj, attr)

    return get_source_class(type(obj), attr)

def get_source_class(obj, attr=None):
    if attr is None:
        attr = {}
        for name in dir(obj):
            value = getattr(obj, name)
            if name not in obj.__dict__:
                continue
            if name.startswith(('_', '__')) and value is None:
                continue
            attr[name] = value
    pat = "class {cls_name}({parents}):\n" \
          "\t{defs}\n".expandtabs(4)
    defs = join_functions(obj, attr, sep='\n' +' '*4,
                                   in_func_sep='\n' +' '*4)
    return pat.format(cls_name=obj.__name__,
                      parents=', '.join(t.__name__ for t in obj.__bases__),
                      defs=defs,)

def join_functions(obj, attr=None, sep='\n\n', in_func_sep='\n'):
    if attr is None:
        attr = {name: getattr(obj, name) for name in dir(obj)}

    defs = []
    for name, val in attr.iteritems():
        spec = getattr(val, SRC_LABEL_ATTR, False)

        if inspect.isroutine(val) and not spec:
            try:
                spec = cut_excess(inspect.getsource(val))
            except (TypeError, IOError):
                spec = str(val)
        else:
            if not spec:
                spec = val
            spec = '{} = {}'.format(name, str(spec))
        defs.append(in_func_sep.join(spec.splitlines()))

    defs.sort()
    return sep.join(defs)

def cut_excess(func_source, exclude=None):
    slocs = func_source.expandtabs(4).splitlines()
    spaces = len(slocs[0]) - len(slocs[0].lstrip())

    if not spaces:
        return func_source
    if exclude is None:
        return '\n'.join(s and s[spaces:] for s in slocs)
    exclude = set(exclude) if isinstance(exclude, (tuple, list)) else exclude

    pred = lambda s: not (s and s[spaces:] in exclude)
    slocs = '\n'.join(s[spaces:] for s in slocs if pred(s))

    return slocs

def split_on_last_method(args):
    arg = args.object.strip()
    try:
        obj, method_name = arg.rsplit('.', 1)
    except ValueError:
        obj, method_name = arg.split()
    return obj, method_name

    