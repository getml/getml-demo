from getml_binder_init import watch_log, get_environment
from pathlib import Path
import sys

home = Path.home()
sys.stdout.write(home)
env = get_environment("/home/jovyan/.getML")
sys.stdout.write(env)
watch_log("/home/jovyan/binder/getml.out.log", env)