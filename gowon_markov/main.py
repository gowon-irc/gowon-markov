#!/usr/bin/env python

import json
import re
import logging
import contextlib
import socket
import time

import configargparse
import markovify
import paho.mqtt.client as mqtt

from gowon_markov import markov, cache

MODULE_NAME = "markov"


def on_connect(client, userdata, flags, rc):
    logging.info(f"Connected with result code {rc}")

    client.subscribe("/gowon/input")


def gen_on_message_handler(model_cache):
    def f(client, userdata, msg):
        try:
            msg_in_json = json.loads(msg.payload.decode())
        except JSONDecodeError:
            logging.error("Error parsing message json")
            return

        command = msg_in_json["command"]

        if command not in model_cache.model_fns:
            return

        logging.info(f"Fetching model for {command}")
        model = model_cache.get(command)

        if model is None:
            logging.error(f"No model found for {command}")

        out = model.make_sentence(tries=20)

        if out is None:
            logging.error(f"Could not create sentence from {command} model")

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
    logger = logging.getLogger()
    logger.setLevel("INFO")

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
    p.add("-A", "--cache-age", env_var="GOWON_MARKOV_CACHE_AGE", type=int, default="60")
    p.add(
        "-L",
        "--cache-length",
        env_var="GOWON_MARKOV_CACHE_LENGTH",
        type=int,
        default="1",
    )
    opts = p.parse_args()

    client = mqtt.Client(f"gowon_{MODULE_NAME}")

    client.on_connect = on_connect

    corpus_file_list = markov.split_corpus_arg(opts.corpus)
    corpus_file_list_with_root = markov.corpus_file_list_add_root(
        corpus_file_list, opts.data_dir
    )

    model_cache = cache.ModelCache(
        max_len=opts.cache_age, max_age_seconds=opts.cache_length
    )

    for corpus_file in corpus_file_list_with_root:
        command, fn = corpus_file["command"], corpus_file["fn"]
        model_cache.add_fn(command, fn)

    client.on_message = gen_on_message_handler(model_cache)

    for i in range(12):
        try:
            client.connect(opts.broker_host, opts.broker_port)
        except ConnectionRefusedError:
            logging.error("connection refused, retrying after 5 seconds")
            time.sleep(5)
        else:
            break

    logging.info("Connected to broker")

    client.loop_forever()


if __name__ == "__main__":
    main()
