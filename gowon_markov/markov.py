import markovify

import os


def split_corpus_arg(arg):
    cs = arg.split(",")
    css = [i.split(":") for i in cs]
    args = [dict(zip(("command", "file"), i)) for i in css if len(i) >= 2]

    return args


def add_root_to_corpus_file_dict(corpus_dict, root):
    new_file = os.path.join(root, corpus_dict["file"])

    return {**corpus_dict, **{"file": new_file}}


def corpus_file_list_add_root(corpus_list, root):
    return [add_root_to_corpus_file_dict(i, root) for i in corpus_list]


def create_model_dict(corpus_list):
    def get_corpus(fn):
        with open(fn) as f:
            text = f.read()

        model = markovify.NewlineText(text, retain_original=False)
        return model.compile()

    return {i["command"]: get_corpus(i["file"]) for i in corpus_list}
