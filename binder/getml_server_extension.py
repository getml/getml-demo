import os
import re
import time
from pathlib import Path
from subprocess import STDOUT, Popen

from itertools import chain
from pathlib import Path


def walk(path=".", globs=(["*"])):
    paths = [Path(path).rglob(ext) for ext in globs]
    files = chain(*paths)
    return files
    

def replace_monitor_refs(user_base, globs):
    for fp in walk(globs=globs):
        with open(fp, "r+") as f:
            project = fp.stem
            content = f.read()
            content = re.sub(
                r"(url:\s<a\b[^>]*>.*?<\/a>)",
                "url: [INFO] rerun notebook to use the getML Monitor for exploration",
                content,
            )
            content = re.sub(
                r"(http:\/\/localhost:1709)",
                user_base + r"proxy/1709/#/listpipelines/" + project,
                content,
            )

            # nb_node = nbformat.reads(content, as_version=4)
            # nbformat.write(nb_node, fp)
            f.seek(0)
            f.write(content)
            f.truncate()


def load_jupyter_server_extension(nbapp):
    web_app = nbapp.web_app
    user_base = web_app.settings["base_url"]
    home = Path.home()
    getml_dl_dir = home / ".binder/getml"

    with open(home / ".binder/getml.log", "wb") as e_log:
        Popen(
            [
                "./getML",
                "--install",
                "--proxy-url",
                user_base + "proxy/1709",
                "--http-port",
                "1709",
            ],
            cwd=getml_dl_dir,
            stdout=e_log,
            stderr=STDOUT,
        )

    # pass base url to markdown
    with open(home / "welcome.md", "r+") as f:
        content = f.read()

        f.seek(0)
        f.write(
            re.sub(r"(http:\/\/localhost:1709)", user_base + r"proxy/1709/", content)
        )
        f.truncate()

    replace_monitor_refs(user_base, ["*.ipynb"])

    time.sleep(7)

    os.system(f'cd {home} && git commit -a -m "postBuild complete"')
