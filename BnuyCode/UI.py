from __future__ import annotations
import sys
import json
import time
import urwid as ui

class Interface():
    def __init__(self, main_obj):
        self.main_obj = main_obj
        self.write_fd = None
        self.loop = None

        #### BUTTON SECTION
        self.exit_button = ui.Button("Exit")

        ui.connect_signal(self.exit_button, "click", self.stop_program)

        #### COLORS
        self.palette = [
                ("err", "white", "dark red"), # for errors
                ("clr_err", "default", "default") # empty a row
                ]

        #### MESSAGES
        self.messages = []

        self.message_list = ui.SimpleFocusListWalker([])
        self.message_view = ui.ListBox(self.message_list)

    def callback(self, data: bytes) -> None:
        message = data.decode()
        message = json.loads(message)

        def msg_unpack(message):
            message_dict = message
            sender = message_dict.get("sender")
            content = message_dict.get("content")

            return sender, content, message_dict

        if isinstance(message, list):
            for nested_msg in message:
                sender, content, message_dict = msg_unpack(nested_msg)
                self.messages.append(message_dict)
                self.message_list.append(self.draw_message(sender, content))

        else: 
            sender, content, message_dict = msg_unpack(message)

            self.messages.append(message_dict)
            self.message_list.append(self.draw_message(sender, content))
        if self.loop is not None: self.loop.draw_screen()


    def run_menu(self, menu, input=None):
        if input != None:
            self.loop = ui.MainLoop(menu, self.palette, unhandled_input=input)
        else:
            self.loop = ui.MainLoop(menu, self.palette)
        self.write_fd = self.loop.watch_pipe(self.callback)
        self.loop.run()

        while self.main_obj.sending_post: time.sleep(0.10)
        self.write_fd = None

    def stop_program(self, _button: ui.Button) -> None:
        sys.exit()

    #### User viewed stuff

    def signup(self):
        ip = ui.Edit(">>> ")
        name = ui.Edit(">>> ")
        password = ui.Edit(">>> ")
        err = ui.Text("")
        err_map = ui.AttrMap(err, "clr_err")

        class Page(ui.Frame):

            def keypress(self, size, key):
                if key != "enter": 
                    err_map.set_attr_map({None: "clr_err"})
                    err.set_text("")
                    return super().keypress(size, key)

                else: 
                    ip_len = len(ip.get_edit_text())
                    name_len = len(name.get_edit_text())
                    password_len = len(password.get_edit_text())
                    if ip_len and name_len and password_len:
                        raise ui.ExitMainLoop
                    else:
                        err_map.set_attr_map({None: "err"})
                        err.set_text("Please fill in every field before entering!")


        form = ui.Pile([
            ui.LineBox(ui.Text("""Welcome to TermChat! :3
To continue, please fill these fields
(Note: Your DNS/IP and password are stored on-device and encrypted.)""")),

            ui.Divider("-"),

            ui.Text("Please enter a DNS/IP (excluding a port)"),
            ui.Text("(For the person you'd like to contact.)"),
            ip,

            ui.Divider("-"),

            ui.Text("Please enter a name"),
            ui.Text("(Do not use your real name!)"),
            name,

            ui.Divider("-"),

            ui.Text("Enter a password."),
            password,

            ui.Divider("-")
            ])

        buttons = ui.Columns([
            self.exit_button,
            ])

        login = Page(ui.LineBox(form),
                      header=err_map,
                      footer=ui.LineBox(buttons), 
                      focus_part="body")

        self.run_menu(login)

        return {
                "ip": ip.get_edit_text(),
                "name": name.get_edit_text(),
                "pass": password.get_edit_text(),
                }

    def draw_message(self, sender, content):
        message = ui.Pile([
                ui.Text(f"Name) {sender}"),
                ui.Divider("-"),
                ui.Text(content),
                ui.Divider("-"),
                ui.Text("")
            ])
        return message

    def chat_menu(self, username):
        interface = self
        text_box = ui.Edit(">>> ")
        
        def draw_message_list():

            for message_metadata in self.messages:
                sender = message_metadata.get("sender")
                content = message_metadata.get("content")
                message = self.draw_message(sender, content)

                if message not in self.message_list:
                    self.message_list.append(message)
                    self.message_list.set_focus(len(self.message_list)-1)

        class Page(ui.Frame):
            def keypress(self, size, key):
                if key != "enter":
                    return super().keypress(size, key)
                else: 
                    if len(text_box.get_edit_text()) > 1:
                        interface.messages.append(interface.main_obj.data["receiver"],
                                                  username,
                                                  text_box.get_edit_text(),)
                        interface.message_list.append(
                            interface.draw_message(username, text_box.get_edit_text())
                            )
                        raise ui.ExitMainLoop()


        chat_box = ui.Columns([
            text_box, self.exit_button
            ])

        draw_message_list()
        chat = Page(ui.LineBox(self.message_view),
                        footer=ui.LineBox(chat_box),
                        focus_part="footer",
                        )

        self.run_menu(chat)
        return text_box.get_edit_text()


if __name__ == "__main__":
    from . import Client
    uitest = Interface(Client())
    uitest.chat_menu("test")
