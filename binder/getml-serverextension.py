import os
import sys
import re
import requests as req
from subprocess import Popen, PIPE, STDOUT


def load_jupyter_server_extension(nbapp):
    web_app = nbapp.web_app
    user_base = web_app.settings['base_url']

    with open("/home/jovyan/binder/getml.log", "wb") as out, open("/home/jovyan/binder/stderr.log", "wb") as err:
        Popen(["./getML", "--install", "--proxy-url",
               user_base+"proxy/1709", "--http-port", "1709"],
              cwd="/home/jovyan/binder/getml/", stdout=out, stderr=err)

    # pass base url to markdown
    with open('/home/jovyan/welcome.md', 'r+') as f:
        content = f.read()
        f.seek(0)
        f.write(re.sub(r'(http:\/\/localhost:1709)',
                       user_base + r'proxy/1709/', content))
        f.truncate()
