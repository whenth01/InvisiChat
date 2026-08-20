from __future__ import annotations

import urwid as ui
# this was used to hwlp me learn urwid
class TextBox(ui.LineBox):
    def keypress(self, size, key):
        if key != "enter":
            return super().keypress(size, key)

        self.original_widget = ui.Text(f"User: {edit.edit_text}")
        return None

def show_or_exit(key):
    if key.lower() in "q":
        raise ui.ExitMainLoop()

edit = ui.Edit("Send a message) ")
fill = TextBox(edit)
loop = ui.MainLoop(fill, unhandled_input=show_or_exit)
loop.run()
