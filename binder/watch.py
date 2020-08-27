from getml_binder_init import watch_log, get_environment
from pathlib import Path
import sys

home = Path.home()
sys.stdout.write(home)
env = get_environment(home / ".getML")
sys.stdout.write(env)
watch_log(home / "binder/getml.out.log", env)