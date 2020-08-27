import os
import re
from pathlib import Path
from subprocess import Popen, run
from getml_binder_init import get_environment, add_telemetry, watch_log
import time


def load_jupyter_server_extension(nbapp):
    web_app = nbapp.web_app
    user_base = web_app.settings['base_url']
    home = Path.home()
    getml_dl_dir = home / "binder/getml"
    getml_dir = home / ".getML/getml-0.12-beta-linux/"

    with open(home / "binder/getml.out.log", "wb") as out, open(home / "binder/getml.err.log", "wb") as err:
        Popen(["./getML", "--install", "--proxy-url",
               user_base+"proxy/1709", "--http-port", "1709"],
              cwd=getml_dl_dir, stdout=out, stderr=err)

    # pass base url to markdown
    with open(home / 'welcome.md', 'r+') as f:
        content = f.read()
        f.seek(0)
        f.write(re.sub(r'(http:\/\/localhost:1709)',
                       user_base + r'proxy/1709/', content))
        f.truncate()

    time.sleep(5)
    env = get_environment("~/.getML")
    add_telemetry(["*.md", "*.ipynb"], env)

    with open(home / "binder/watch.out.log", "wb") as wout, open(home / "binder/watch.err.log", "wb") as werr:
        Popen(["/srv/conda/envs/notebook/bin/python", "watch.py"],
              cwd=home / "binder", stdout=wout, stderr=werr)
