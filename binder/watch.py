from getml_binder_init import watch_log, get_environment

env = get_environment("~/.getML")
print(env)
watch_log("~/binder/getml.out.log", env)
