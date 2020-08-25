import os
import sys
import re
import requests as req
import pathlib
from subprocess import Popen, PIPE, STDOUT
# from getml_binder import binder_init


def get_environment(getml_dir):
    getml_env_file = getml_dir / "environment.json"
    binder_ref = os.environ.get("BINDER_REF_URL")
    client_id = os.environ.get("JUPYTERHUB_CLIENT_ID")

    with open(getml_env_file) as f:
        getml_env = json.load(f)
        license_seed = getml_env['monitor']['licenseSeedStatic']
        while lecense_seed < 0:
            getml_env = json.load(f)
            license_seed = getml_env['monitor']['licenseSeedStatic']

    return binder_ref, client_id, license_seed


def load_jupyter_server_extension(nbapp):
    web_app = nbapp.web_app
    user_base = web_app.settings['base_url']
    home = pathlib.Path.home()
    getml_dir = home / "binder/getml"

    with open(home / "binder/getml.log", "wb") as out, open(home / "binder/stderr.log", "wb") as err:
        install = Popen(["./getML", "--install", "--proxy-url",
                         user_base+"proxy/1709", "--http-port", "1709"],
                        cwd=getml_dir, stdout=out, stderr=err)
        env = get_environment(getml_dir)

        while env[3] < 0:
            env = get_environment(getml_dir)

    # pass base url to markdown
    with open(home/'welcome.md', 'r+') as f:
        content = f.read()
        f.seek(0)
        f.write(re.sub(r'(http:\/\/localhost:1709)',
                       user_base + r'proxy/1709/', content))
        f.write(env)
        f.truncate()
