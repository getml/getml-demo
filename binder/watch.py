from getml_binder_init import watch_log, get_environment

env = get_environment("/home/jovyan/.getML")
print(env)
watch_log("/home/jovyan/binder/getml.out.log", env)
