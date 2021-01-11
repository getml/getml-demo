# Jupyter notebook config
# https://jupyter-notebook.readthedocs.io/en/stable/config.html#options


# Jupyter server proxy config
# https://github.com/jupyterhub/jupyter-server-proxy
# https://jupyter-server-proxy.readthedocs.io/en/latest/index.html

# getml_cmd = ' '.join([
#     # '/home/jovyan/binder/run_getml.sh "$1" "$2"', '{base_url}', '{port}'
# ])
# '/bin/bash', '-c', f'{getml_cmd}'],

# getml_cmd = ' '.join([
#     'getML', '--install', '--proxy-url', '{base_url}getml/', '--http-port', '{port}',
#     '--engine-port', '1808',
#     '--https-port', '1810',
#     '--tcp-port', '1811'
# ])


# c.ServerProxy.servers = {
#     'getml': {
#         'command': [
#             '/bin/bash', '-c',
#             f'{getml_cmd} >getml.log 2>&1'],
#         'absolute_url': False,
#         'port': 1809,
#         'timeout': 15,
#         'launcher_entry': {
#             'title': 'getML Monitor',
#             # must be an svg
#             # 'icon_path': '/home/jovyan/.jupyter/getml_logo.png'
#         }

#     }
# }
c.SlidesExporter.reveal_scroll = True
# c.SlidesExporter.reveal_theme = "solarized"


# See https://github.com/jupyter-server/jupyter-resource-usage/blob/master/CHANGELOG.md
# relevant packages: jupyterlab-system-monitor, jupyter-resource-usage, nbresuse


# c.NotebookApp.ResourceUseDisplay.track_cpu_percent = True
# c.NotebookApp.ResourceUseDisplay.disable_legacy_endpoint=False

c.NotebookApp.tornado_settings = {"autoreload": True}

# shutdown parameters of images/ user pods from jupyterhub
# https://jupyterhub.readthedocs.io/en/stable/reference/config-user-env.html
# https://github.com/jupyterhub/mybinder.org-deploy/blob/master/mybinder/values.yaml
# https://jupyter-notebook.readthedocs.io/en/stable/config_overview.html
# https://jupyter-notebook.readthedocs.io/en/stable/config.html
# https://jupyter-contrib-nbextensions.readthedocs.io/en/latest/config.html
