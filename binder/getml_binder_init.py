import base64
import datetime
import json
import os
import re
import sys
import time
from itertools import chain
from pathlib import Path

import nbformat
import requests
from watchgod import watch


def get_environment(getml_dir):
    getml_dir = Path(getml_dir).expanduser()
    getml_env_file = getml_dir / "getml-0.14-beta-linux/environment.json"

    env = dict()
    env['binder_ref'] = os.environ.get("BINDER_REF_URL")
    env['binder_request'] = os.environ.get("BINDER_REQUEST")
    env['client_id'] = os.environ.get("JUPYTERHUB_CLIENT_ID")
    env['jupyter_image'] = os.environ.get("JUPYTER_IMAGE")
    env['binder_cluster'] = env['jupyter_image'].split('/')[0]

    with open(getml_env_file) as f:
        getml_env = json.load(f)
        env['license_seed'] = getml_env['monitor']['licenseSeedStatic']

    return env


def append_cell(fp, telemetry):
    with open(fp) as nb:
        nb_node = nbformat.read(nb, as_version=4)
        telemetry_cell = nbformat.v4.new_markdown_cell(
            "![]("+telemetry+")")
        nb_node.cells.append(telemetry_cell)
        nbformat.write(nb_node, os.fspath(fp))


def append_md(fp, telemetry):
    with open(fp, "a+") as f:
        f.write("![]("+telemetry+")")


def walk(path=".", globs=(["*"])):
    paths = [Path(path).rglob(ext) for ext in globs]
    files = chain(*paths)
    return files


def encode_dict(dict_):
    telemetry_encoded = "https://api.segment.io/v1/pixel/page?data="
    telemetry_encoded += base64.urlsafe_b64encode(
        json.dumps(dict_).encode("utf-8")).decode()
    return telemetry_encoded


def add_telemetry(globs, env):
    for fp in walk(globs=globs):
        env['file_name'] = fp.name
        telemetry = dict()
        telemetry["writeKey"] = "YBF9q7cBQqgmbR0DyR5jyB7QNW2xjwHm"
        telemetry["anonymousId"] = env["license_seed"]
        telemetry["properties"] = env
        path = str(fp.absolute().relative_to(Path.home()).parent)
        # telemetry["properties"]["url"] = "https://demo.getml.com/" + env["binder_request"] + "/" + str(fp)
        telemetry["properties"]["path"] = "/" + \
            "/".join(env["binder_request"].split("/")[-2:])
        telemetry["properties"]["path"] += "/" + path if path != "." else ""
        telemetry["properties"]["path"] += "/" + env['file_name']
        telemetry["properties"]["url"] = "https://demo.getml.com" + \
            telemetry["properties"]["path"] + "/" + env['file_name']
        telemetry["properties"]["title"] = env["file_name"]
        telemetry["context"] = {
            "page": {
                "title": telemetry["properties"]["title"]
            }
        }
        if fp.suffix == ".md":
            telemetry = encode_dict(telemetry)
            append_md(fp, telemetry)
        elif fp.suffix == ".ipynb":
            telemetry = encode_dict(telemetry)
            append_cell(fp, telemetry)


def send_watch_event(event, label, env):
    headers = dict()
    headers["Content-Type"] = "application/json"
    headers["Authorization"] = "Basic "
    headers["Authorization"] += base64.urlsafe_b64encode(
        "YBF9q7cBQqgmbR0DyR5jyB7QNW2xjwHm".encode('utf-8')).decode()
    telemetry = dict()
    telemetry["anonymousId"] = env["license_seed"]
    telemetry["properties"] = env
    telemetry["properties"]["path"] = "/" + \
        "/".join(env["binder_request"].split("/")[-2:])
    telemetry["properties"]["url"] = "https://demo.getml.com" + \
        telemetry["properties"]["path"]
    telemetry["properties"]["commit"] = env["binder_ref"].split("/")[-1]
    telemetry["properties"]["v"] = env["binder_request"].split("/")[-1]
    telemetry["properties"]["category"] = "getml-demo " + \
        telemetry["properties"]["v"]
    telemetry["event"] = event
    telemetry["properties"]["label"] = label
    resquest_destination = "https://api.segment.io/v1/track"
    res = requests.request(
        "POST", resquest_destination, headers=headers, json=telemetry, timeout=5).json()
    print(res)


def watch_log(log_file, env):
    log_file = Path(log_file).expanduser()
    if log_file.exists():
        for changes in watch(log_file):
            with open(log_file, "r") as f:
                log = f.read()
                try:
                    log = log.splitlines()[-4:-1]
                    # time = datetime.datetime.strptime(
                    #     log[0], "%a %b %d %H:%M:%S %Y")
                    command = json.loads(log[2])
                    if command["type_"] == "set_project":
                        send_watch_event("Engine: Set project",
                                         command["name_"], env)
                        # print("Set Project to", project, "at", time)
                    if command["type_"] == "Pipeline.fit":
                        send_watch_event(
                            "Engine: Pipeline fitted", "fitted", env)
                        # print("Fitted a pipeline in project", project, "at", time)
                        # print(command, time)
                except:
                    sys.stdout.write(str(log))


def load_jupyter_server_extension(nbapp):
    pass
