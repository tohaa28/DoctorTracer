"""Stage progress for the tracing worker; independent of elapsed time."""
def report(cfg,percent,stage):
    callback=cfg.get('_progress')
    if callback:callback(int(percent),stage)
