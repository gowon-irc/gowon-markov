#!/usr/bin/env python

import argparse
import os
import sys
import datetime
import logging

import markovify


def filter_messages(log):
    return [i for i in log if "<" in i]


def get_user(line):
    if "<" not in line:
        return None

    return line.split("<")[1].split(">")[0]


def filter_user(log, user):
    return [i for i in log if get_user(i) == user]


def get_date_string(line):
    return line[1:20]


def get_datetime(dt):
    return datetime.datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")


def filter_datetime(log, dt):
    return [i for i in log if get_datetime(get_date_string(i)) > dt]


def filter_metadata(log):
    return [i.split(">")[1][1:] for i in log]


def main():
    ap = argparse.ArgumentParser("Convert irccloud logs to markov model json files")
    ap.add_argument("-f", "--file", required=True, help="input log file")
    ap.add_argument("-o", "--output", required=True, help="output json model file")
    ap.add_argument("-u", "--user", help="filter by user")
    ap.add_argument("-l", "--lines", type=int, help="only use last n lines")
    ap.add_argument(
        "-T", "--datetime", help="filter messages to after datetime (%Y-%m-%d %H:%M:%S)"
    )
    ap.add_argument(
        "-L",
        "--loglevel",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="WARNING",
        help="log level",
    )
    args = ap.parse_args()

    logger = logging.getLogger()
    logger.setLevel(args.loglevel)

    if not os.path.exists(args.file):
        print(f"Error: {args.file} does not exist", file=sys.stderr)

    with open(args.file) as f:
        logging.debug(f"opening log file {args.file}")
        log = [i.strip() for i in f.readlines()]

    logging.debug("filtering out any meta messages")
    log = filter_messages(log)

    if args.user:
        logging.info(f"filtering log to only lines by {args.user}")
        log = filter_user(log, args.user)

    if args.lines:
        logging.info(f"filtering log to last {args.lines} lines")
        log = log[-args.lines :]

    if args.datetime:
        logging.info(f"filtering log to lines after {args.datetime}")
        filter_dt = get_datetime(args.datetime)
        log = filter_datetime(log, filter_dt)

    logging.info(f"using {len(log)} lines for model")

    logging.info("filtering out metadata from lines")
    log = filter_metadata(log)

    corpus = "\n".join(log)

    logging.info("creating model from selected lines")
    model = markovify.NewlineText(corpus)

    logging.info("converting model to json")
    model_json = model.to_json()

    logging.info(f"writing json model to {args.output}")
    with open(args.output, "w") as f:
        f.write(model_json)


if __name__ == "__main__":
    main()
