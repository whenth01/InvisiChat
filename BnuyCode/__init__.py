import sys
import urwid
version = "Test build V1.0.18"

def bnuy_except_hook(exctype, value, traceback):
    """Custom messages for exceptions"""

    if exctype == KeyboardInterrupt:
        sys.exit()

    elif exctype == urwid.widget.widget.WidgetError:
        print("TermChat encountered a WidgetError")
        print("Your terminal may be too small! :(")
        sys.exit()
    
    else:
        sys.__excepthook__(exctype, value, traceback)


sys.excepthook = bnuy_except_hook
