#!/usr/bin/env python

import json
import re
import logging
import contextlib
import socket
import time
import threading
import gc

import configargparse
import markovify
import cachetools
import paho.mqtt.client as mqtt

from gowon_markov import markov

MODULE_NAME = "markov"

CACHE_EXPIRE_INTERVAL = 300


def on_connect(client, userdata, flags, rc):
    logging.info(f"Connected with result code {rc}")

    client.subscribe("/gowon/input")


class RepeatTimer(threading.Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


def gen_on_message_handler(corpus_dict, cache):
    @cachetools.cached(cache=cache)
    def cached_open_model(fn):
        return markov.open_model(fn)

    def f(client, userdata, msg):
        try:
            msg_in_json = json.loads(msg.payload.decode())
        except JSONDecodeError:
            logging.error("Error parsing message json")
            return

        command = msg_in_json["command"]
        corpus_fn = corpus_dict.get(command)

        if not corpus_fn:
            return

        logging.info(f"Fetching model for {command}")
        model = cached_open_model(corpus_fn)

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


def gen_cache_clear(cache):
    def cache_clear():
        logging.info("Clearing cache and running garbage collection")
        cache.expire()
        gc.collect()
    return cache_clear


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
    p.add("-L", "--cache-size", env_var="GOWON_MARKOV_CACHE_SIZE", type=int, default=1)
    p.add("-A", "--cache-ttl", env_var="GOWON_MARKOV_CACHE_TTL", type=int, default=60)
    opts = p.parse_args()

    client = mqtt.Client(f"gowon_{MODULE_NAME}")

    client.on_connect = on_connect

    corpus_fn_list = markov.split_corpus_arg(opts.corpus)
    corpus_abs_fn_list = markov.corpus_abs_file_list(corpus_fn_list, opts.data_dir)
    corpus_fn_dict = {i["command"]: i["fn"] for i in corpus_abs_fn_list}

    cache = cachetools.TTLCache(maxsize=opts.cache_size, ttl=opts.cache_ttl)

    t = RepeatTimer(CACHE_EXPIRE_INTERVAL, gen_cache_clear(cache))
    t.start()

    client.on_message = gen_on_message_handler(corpus_fn_dict, cache)

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

    t.cancel()


if __name__ == "__main__":
    main()
