import markovify

import os


def split_corpus_arg(arg):
    cs = arg.split(",")
    css = [i.split(":") for i in cs]
    args = [dict(zip(("command", "fn"), i)) for i in css if len(i) >= 2]

    return args


def add_root_to_corpus_file_dict(corpus_dict, root):
    new_file = os.path.join(root, corpus_dict["fn"])

    return {**corpus_dict, **{"fn": new_file}}


def corpus_abs_file_list(corpus_list, root):
    return [add_root_to_corpus_file_dict(i, root) for i in corpus_list]


def open_model(fn):
    with open(fn) as f:
        model = markovify.NewlineText(f)

    return model
