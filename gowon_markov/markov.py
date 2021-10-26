import markovify

import os


def split_model_arg(arg):
    cs = arg.split(",")
    css = [i.split(":") for i in cs]
    args = [dict(zip(("command", "fn"), i)) for i in css if len(i) >= 2]

    return args


def add_root_to_model_file_dict(model_dict, root):
    new_file = os.path.join(root, model_dict["fn"])

    return {**model_dict, **{"fn": new_file}}


def model_abs_file_list(model_list, root):
    return [add_root_to_model_file_dict(i, root) for i in model_list]


def open_model(fn):
    with open(fn) as f:
        model = markovify.NewlineText.from_json(f.read())

    return model
