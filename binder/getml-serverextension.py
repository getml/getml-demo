import os
import sys
import re
import requests as req
import json
import nbformat
import time
from pathlib import Path
from itertools import chain
from subprocess import Popen, PIPE, STDOUT
# from getml_binder import binder_init


def get_environment(getml_dir):
    getml_env_file = getml_dir / "environment.json"
    binder_ref = os.environ.get("BINDER_REF_URL")
    client_id = os.environ.get("JUPYTERHUB_CLIENT_ID")

    with open(getml_env_file) as f:
        getml_env = json.load(f)
        license_seed = getml_env['monitor']['licenseSeedStatic']

    return binder_ref, client_id, license_seed


def append_cell(fp, telemetry):
    with open(fp) as nb:
        nb_node = nbformat.read(nb, as_version=4)
        telemetry_cell = nbformat.v4.new_markdown_cell(
            "![]("+telemetry+")")
        nb_node.cells.append(telemetry_cell)
        nbformat.write(nb_node, fp)


def append_md(fp, telemetry):
    with open(fp, 'a+') as f:
        f.write("![]("+telemetry+")")


def walk(path=".", exts=("*")):
    paths = [Path(path).rglob(ext) for ext in exts]
    files = chain(*paths)
    return files


def add_telemetry(exts, telemetry):
    for fp in walk(exts=exts):
        if fp.suffix == "*.md":
            append_cell(f, telemetry)
        elif fp.suffix == "*.ipynb":
            append_md(fp, telemetry)


def load_jupyter_server_extension(nbapp):
    web_app = nbapp.web_app
    user_base = web_app.settings['base_url']
    home = Path.home()
    getml_dir = home / "binder/getml"

    with open(home / "binder/getml.log", "wb") as out, open(home / "binder/stderr.log", "wb") as err:
        Popen(["./getML", "--install", "--proxy-url",
               user_base+"proxy/1709", "--http-port", "1709"],
              cwd=getml_dir, stdout=out, stderr=err)
        time.sleep(5)
        env = get_environment(getml_dir)

    # pass base url to markdown
    with open(home / 'welcome.md', 'r+') as f:
        content = f.read()
        f.seek(0)
        # f.write(re.sub(r'(http:\/\/localhost:1709)',
        #                user_base + r'proxy/1709/', content))
        f.write(str(env))
        f.truncate()
