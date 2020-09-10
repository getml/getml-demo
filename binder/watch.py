from getml_binder_init import watch_log, get_environment
from pathlib import Path
import sys

home = Path.home()
sys.stdout.write(str(home))
env = get_environment(home / ".getML")
sys.stdout.write(str(env))
watch_log(home / ".binder/getml.log", env)