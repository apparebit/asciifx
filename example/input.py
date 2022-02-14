#[keypress-speed=0.6]
#[off]
import konsole
konsole.config(use_color=True)
#[on]
konsole.info("fyi", detail=["for", "your", "information"])
konsole.warning("beware")
konsole.error("bad")
konsole.critical("enough already!!!")
quit()
