from __future__ import annotations
import sys
import json
import uuid as id_gen
import time
import urwid as ui


class Interface():
    def __init__(self, main_obj):
        self.main_obj = main_obj
        self.screen = ui.raw_display.Screen()
        self.write_fd = None
        self.loop = None
        self.return_called = False
        self.main_menu_widget = None

        #### BUTTON SECTION
        self.exit_button = ui.Button("Exit")
        self.chat_button = ui.Button("Open chat")
        self.back_button = ui.Button("Back")

        ui.connect_signal(self.exit_button, "click", self.stop_program)
        ui.connect_signal(self.chat_button, "click", self.main_obj.send_msg)
        ui.connect_signal(self.back_button, "click", self.go_to_mainmenu)

        #### COLORS
        self.palette = [
                ("err", "white", "dark red"), # for errors
                ("clr_err", "default", "default") # empty a row
                ]

        #### MESSAGES
        self.messages = dict()

        self.message_list = ui.SimpleFocusListWalker([])
        self.message_view = ui.ListBox(self.message_list)
        self.message_ids = dict()

    def go_to_mainmenu(self, button):
        self.loop.widget = self.main_menu_widget

    def add_msgs(self, message_dict):
        uuid = list(message_dict.keys())[0]

        if self.messages.get(uuid) is None:
            self.message_ids[uuid] = set()
            self.messages[uuid] = []

        sender = message_dict[uuid]["sender"]
        content = message_dict[uuid]["content"]
        id = message_dict[uuid]["id"]

        self.message_ids[uuid].add(id)
        self.messages[uuid].append(message_dict[uuid])
        self.message_list.append(self.draw_message(sender, content))

    #### This is used for getting messages from server.py!!!
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
                _, _, message_dict = msg_unpack(nested_msg)
                self.add_msgs(message_dict)

        else: 
            _, _, message_dict = msg_unpack(message)
            self.add_msgs(message_dict)
        if self.loop is not None: self.loop.draw_screen()


    def run_menu(self, menu, input=None):

        if input != None:
            self.loop = ui.MainLoop(menu, self.palette, 
                                    unhandled_input=input, screen=self.screen)
        else:
            self.loop = ui.MainLoop(menu, self.palette, screen=self.screen)
        self.write_fd = self.loop.watch_pipe(self.callback)
        self.loop.run()

        while self.main_obj.sending_post: time.sleep(0.10)
        self.loop = None
        self.write_fd = None

    def stop_program(self, _button: ui.Button) -> None:
        sys.exit()

    #### User viewed stuff

    def signup(self, callback_method):
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
                        callback_method(dict(ip=ip.get_edit_text(),
                                             name=name.get_edit_text(),
                                             password=password.get_edit_text()))
                        raise ui.ExitMainLoop()
                    else:
                        err_map.set_attr_map({None: "err"})
                        err.set_text("Please fill in every field before entering!")


        form = ui.Pile([
            ui.LineBox(ui.Text("""Welcome to TermChat! :3
To continue, please fill these fields
(Note: Your DNS/IP and password are stored on-device and encrypted.)""")),

            ui.Divider("-"),

            ui.Text("Please enter a DNS/IP (excluding a port)"),
            ui.Text("(This is how people can chat to you!)"),
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
        if self.loop is None:
            self.run_menu(login)
        else:
            self.loop.widget = login

    def main_menu(self):
        text_box = ui.Edit(">>> ")

        buttons = ui.Pile([
            ui.Columns([
                ui.Text("Exit & Settings"),
                self.exit_button,
                ]),

            ui.Divider("-"),

            ui.Columns([
                ui.Text("Chat stuff) "),
                self.chat_button,
                ]),

            ui.Divider("-"),
            ])

        main = ui.Frame(
                ui.LineBox(buttons),
                header=ui.Text("Welcome back to TermChat!:3"),
                footer=ui.LineBox(ui.Text("Version) V0.0.2")),
                focus_part=("body"),
                )
        self.main_menu_widget = main
        if self.loop is None:
            self.run_menu(main)
        else:
            self.loop.widget = main

    def draw_message(self, sender, content):
        message = ui.Pile([
                ui.Text(f"{sender})"),
                ui.Divider("-"),
                ui.Text(content),
                ui.Divider("-"),
                ui.Text("")
            ])
        return message

    def draw_message_list(self, uuid):
        if self.messages.get(uuid) is None:
            return
        for message_metadata in self.messages.get(uuid):
            sender = message_metadata.get("sender")
            content = message_metadata.get("content")
            id = message_metadata.get("id")
            
            messages_by_id = self.message_ids.get(uuid)

            if messages_by_id is None or id not in messages_by_id:
                self.message_ids[uuid].add(id)
                message = self.draw_message(sender, content)

                self.message_list.append(message)
                self.message_list.set_focus(len(self.message_list)-1)


    def draw_chatbox(self, button, uuid):
        self.draw_message_list(uuid)

    def chat_menu(self, callback_method):

        text_box = ui.Edit(">>> ")
        text_box_draw = ui.Columns([
            ("weight", 3, text_box,),
            ("pack", self.exit_button,),
            ("pack", self.back_button,),
            ])

        interface = self
        contact_list = ui.SimpleFocusListWalker([])
        contact_buttons = ui.ListBox(contact_list)
        uuid = self.main_obj.data["uuid"]

        class Page(ui.Frame):
            def keypress(self, size, key):
                if key != "enter":
                    return super().keypress(size, key)
                elif text_box_draw.get_focus_column() > 0:
                    return super().keypress(size, key)
                else: 
                    if len(text_box.get_edit_text()) >= 1:
                        interface.main_obj.data["id"] = str(id_gen.uuid4())
                        message_dict = {
                                uuid: {
                                    "receiver": interface.main_obj.data["receiver"],
                                    "sender": interface.main_obj.data["sender"],
                                    "content": text_box.get_edit_text(),
                                    "id": interface.main_obj.data["id"],
                                    }
                                }
                        interface.add_msgs(message_dict)
                        callback_method(text_box.get_edit_text())
                        text_box.set_edit_text("")


        def generate_buttons():
            for contact_id, stuff in self.messages.items():
                if contact_id != self.main_obj.data["uuid"]:
                    contact_name = stuff[-1].get("sender")
                    button = ui.Button(contact_name)
                    ui.connect_signal(button, "click", 
                                      self.draw_chatbox, 
                                      user_args=[contact_id])

                    contact_list.append(button)

        generate_buttons()
        try:
            default_start = self.messages[uuid][-1]
            default_name = default_start.get("sender")
        except (KeyError, IndexError):
            default_name = "ERR) Unknown name"
        self.draw_chatbox("",uuid)

        menu = ui.Columns([
            ("given",30,contact_buttons,),
            Page(ui.LineBox(self.message_view),
                footer=text_box_draw,
                header=ui.Text(default_name),
                focus_part="footer"),
            ])
        menu.focus_position = 1
        if self.loop is None:
            self.run_menu(menu)
        else: self.loop.widget = menu


if __name__ == "__main__":
    from . import Client
    uitest = Interface(Client())
    uitest.main_menu()
