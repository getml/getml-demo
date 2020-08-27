from getml_binder_init import watch_log, get_environment
from pathlib import Path

home = Path.home()
env = get_environment(home / ".getML")
print(env)
watch_log(home / "binder/getml.out.log", env)
