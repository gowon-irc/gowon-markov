#!/usr/bin/env python

import json
import re
import logging

import configargparse
import paho.mqtt.client as mqtt

from gowon_markov import markov

MODULE_NAME = "markov"


def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")

    client.subscribe("/gowon/input")


def gen_on_message_handler(model_dict):
    def f(client, userdata, msg):
        try:
            msg_in_json = json.loads(msg.payload.decode())
        except JSONDecodeError:
            logging.error("Error parsing message json")
            return

        corpus = model_dict.get(msg_in_json["command"])

        if corpus is None:
            logging.error("no corpus found")
            return

        out = corpus.make_sentence(tries=100)

        msg_out_json = {
            "module": MODULE_NAME,
            "msg": out,
            "nick": msg_in_json["nick"],
            "dest": msg_in_json["dest"],
            "command": msg_in_json["command"],
            "args": msg_in_json["args"],
        }

        client.publish("/gowon/output", json.dumps(msg_out_json))

    return f


def main():
    p = configargparse.ArgParser()
    p.add("-H", "--broker-host", env_var="GOWON_BROKER_HOST", default="localhost")
    p.add(
        "-P",
        "--broker-port",
        env_var="GOWON_BROKER_PORT",
        type=int,
        default=1883,
    )
    p.add("-C", "--corpus", env_var="GOWON_MARKOV_CORPUS", default="")
    p.add("-d", "--data-dir", env_var="GOWON_MARKOV_DATA_DIR", default="")
    opts = p.parse_args()

    client = mqtt.Client(f"gowon_{MODULE_NAME}")

    client.on_connect = on_connect

    corpus_file_list = markov.split_corpus_arg(opts.corpus)
    corpus_file_list_with_root = markov.corpus_file_list_add_root(corpus_file_list, opts.data_dir)
    model_dict = markov.create_model_dict(corpus_file_list_with_root)

    client.on_message = gen_on_message_handler(model_dict)

    client.connect(opts.broker_host, opts.broker_port)

    client.loop_forever()


if __name__ == "__main__":
    main()
