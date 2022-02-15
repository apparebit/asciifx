# https://github.com/apparebit/konsole
#[keypress-speed=0.6]
#[off]
import konsole
konsole.config(use_color=True)
#[on]
konsole.info("fyi", detail="stuff")
konsole.warning("beware")
konsole.error("fail")
konsole.critical("boom!")
quit()
