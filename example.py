#[off]
import konsole
konsole.config(use_color=True)
#[on]
konsole.info("fyi", detail=["for", "your", "information"])
konsole.warning("beware")
#[think=0.3]
konsole.error("bad")
konsole.critical("enough already!!!")
quit()
