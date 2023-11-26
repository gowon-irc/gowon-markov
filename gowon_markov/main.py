#!/usr/bin/env python

import json
import re
import logging
import contextlib
import socket
import time
import threading
import gc
import random

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


def gen_on_message_handler(model_dict, cache, msg_chance, default_model):
    @cachetools.cached(cache=cache)
    def cached_open_model(fn):
        return markov.open_model(fn)

    def f(client, userdata, msg):
        try:
            msg_in_json = json.loads(msg.payload.decode())
        except JSONDecodeError:
            logging.error("Error parsing message json")
            return

        command = msg_in_json.get("command", "none")
        model_fn = model_dict.get(command)

        logging.debug(f"default_model = {default_model}")
        logging.debug(f"model_fn = {model_fn}")
        logging.debug(f"command = {command}")

        if not model_fn:
            r = random.uniform(0, 1)
            logging.debug(f"{r} >= {msg_chance}")

            if default_model is None or r >= msg_chance:
                return

            model_fn = default_model

        logging.info(f"Fetching model for {model_fn}")
        model = cached_open_model(model_fn)

        out = model.make_sentence(tries=20)

        if out is None:
            logging.error(f"Could not create sentence from {command} model")

        msg_out_json = {
            "module": MODULE_NAME,
            "msg": out,
            "nick": msg_in_json["nick"],
            "dest": msg_in_json["dest"],
        }

        if "command" in msg_in_json:
            msg_out_json["command"] = msg_in_json["command"]

        if "args" in msg_in_json:
            msg_out_json["args"] = msg_in_json["args"]

        client.publish("/gowon/output", json.dumps(msg_out_json))

    return f


def gen_cache_clear(cache):
    def cache_clear():
        logging.info("Clearing cache and running garbage collection")
        cache.expire()
        gc.collect()
    return cache_clear


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
    p.add("-m", "--models", env_var="GOWON_MARKOV_MODELS", default="")
    p.add("-d", "--data-dir", env_var="GOWON_MARKOV_DATA_DIR", default="")
    p.add("-L", "--cache-size", env_var="GOWON_MARKOV_CACHE_LENGTH", type=int, default=1)
    p.add("-A", "--cache-ttl", env_var="GOWON_MARKOV_CACHE_TTL", type=int, default=60)
    p.add("-C", "--msg-chance", env_var="GOWON_MARKOV_MSG_CHANCE", type=float, default=0)
    p.add_argument(
        "-l",
        "--loglevel",
        env_var="GOWON_MARKOV_LOG_LEVEL",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="WARNING",
        help="log level",
    )
    opts = p.parse_args()

    logger = logging.getLogger()
    logger.setLevel(opts.loglevel)

    client = mqtt.Client(f"gowon_{MODULE_NAME}")

    client.on_connect = on_connect

    model_fn_list = markov.split_model_arg(opts.models)
    model_abs_fn_list = markov.model_abs_file_list(model_fn_list, opts.data_dir)
    model_fn_dict = {i["command"]: i["fn"] for i in model_abs_fn_list}

    if len(model_abs_fn_list) > 0:
        default_model = model_abs_fn_list[0]["fn"]
    else:
        default_model = None

    cache = cachetools.TTLCache(maxsize=opts.cache_size, ttl=opts.cache_ttl)

    t = RepeatTimer(CACHE_EXPIRE_INTERVAL, gen_cache_clear(cache))
    t.start()

    client.on_message = gen_on_message_handler(model_fn_dict, cache, opts.msg_chance, default_model)

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
