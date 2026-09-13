import sys
import urwid
version = "DEBUG TEST BUILD"

def bnuy_except_hook(exctype, value, traceback):
    """Custom messages for exceptions"""

    if exctype == KeyboardInterrupt:
        sys.exit()

    elif exctype == urwid.widget.widget.WidgetError:
        print("InvisiChat encountered a WidgetError whilst rendering the UI")
        print("Your terminal may be too small! :(")
        sys.exit()

    else:
        sys.__excepthook__(exctype, value, traceback)


sys.excepthook = bnuy_except_hook
