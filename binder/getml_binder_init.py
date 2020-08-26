import os
import re
import json
import base64
import nbformat
import time
import datetime
from pathlib import Path
from itertools import chain
from watchgod import watch


def get_environment(getml_dir):
    getml_dir = Path(getml_dir).expanduser()
    getml_env_file = getml_dir / "getml-0.12-beta-linux/environment.json"

    env = dict()
    env['binder_ref'] = os.environ.get("BINDER_REF_URL")
    env['binder_request'] = os.environ.get("BINDER_REQUEST")
    env['client_id'] = os.environ.get("JUPYTERHUB_CLIENT_ID")
    env['jupyter_image'] = os.environ.get("JUPYTER_IMAGE")
    env['binder_cluster'] = re.search("(\w+)/", env['jupyter_image']).group(1)

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
        env['file_name'] = fp.stem
        telemetry = dict()
        telemetry["writeKey"] = "YBF9q7cBQqgmbR0DyR5jyB7QNW2xjwHm"
        telemetry["anonymousId"] = env["license_seed"]
        telemetry["properties"] = env
        if fp.suffix == ".md":
            telemetry["event"] = "Markdown rendered"
            telemetry = encode_dict(telemetry)
            append_md(fp, telemetry)
        elif fp.suffix == ".ipynb":
            print(fp, env)
            telemetry["event"] = "Notebook rendered"
            telemetry = encode_dict(telemetry)
            append_cell(fp, telemetry)


def watch_log(log_file):
    log_file = Path(log_file).expanduser()
    if log_file.exists():
        for changes in watch(log_file):
            with open(log_file, "r") as f:
                log = f.read().splitlines()[-4:-1]
                time = datetime.datetime.strptime(
                    log[0], "%a %b %d %H:%M:%S %Y")
                command = json.loads(log[2])
            if command["type_"] == "set_project":
                project = command["name_"]
                print("Set Project to", project, "at", time)
            if command["type_"] == "Pipeline.fit":
                print("Fitted a pipeline in project", project, "at", time)
                print(command, time)


def load_jupyter_server_extension(nbapp):
    pass
