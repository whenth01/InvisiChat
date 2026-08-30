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

        self.debug_mode = False

        #### BUTTON SECTION
        self.exit_button = ui.Button("Exit")
        self.chat_button = ui.Button("Open chat")
        self.back_button = ui.Button("Back")
        self.debug_button = ui.Button("Debug mode")

        ui.connect_signal(self.exit_button, "click", self.stop_program)
        ui.connect_signal(self.chat_button, "click", self.main_obj.send_msg)
        ui.connect_signal(self.back_button, "click", self.go_to_mainmenu)
        ui.connect_signal(self.debug_button, "click", self.debug_switch)

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
        
        #### CONTACT BUTTON WIDGETS
        self.contact_list = ui.SimpleFocusListWalker([])
        self.contact_buttons = ui.ListBox(self.contact_list)
        self.already_made_buttons = set()

        #### CHAT HANDLING
        #note: i am afraid this may take me a while :(((
        #current time: 27 Aug 2026, 12:34 AM
        self.chats = dict()
        # note this shiuld always be a uuid
        self.currently_opened_chat = None
        # different from above
        self.current_contact_name = None

    def go_to_mainmenu(self, button):
        self.loop.widget = self.main_menu_widget

    def debug_switch(self, button):
        self.debug_mode = not self.debug_mode
        self.debug_button.set_label(f"Debug mode ({self.debug_mode})")

    def debug_dissector(self, value):
        self.loop.stop()
        print(value)
        input("Enter any key to continue the code: ")
        self.loop.start()

    def debug_dissect_type(self, value):
        self.loop.stop()
        print(type(value), value)
        input("Enter any key to continue the code: ")
        self.loop.start()

    def add_msgs(self, message_dict, skip_check=False, contact_id=None):
        uuid = list(message_dict.keys())[0]
        sender = message_dict[uuid]["sender"]
        content = message_dict[uuid]["content"]
        # i gave up all pretense of clean code whilst making this method

        def init_message_db(id):
            self.message_ids[id] = set()
            self.messages[id] = []

        def save_msg(id, message_dict, msg_id):
            self.messages[id].append(message_dict)

        if contact_id is not None and self.messages.get(contact_id) is None:
            if uuid != self.main_obj.data["uuid"]:
                self.create_contact(contact_id, sender)
            init_message_db(contact_id)

        elif self.messages.get(uuid) is None:
            if uuid != self.main_obj.data["uuid"]:
                self.create_contact(uuid, sender)
            init_message_db(uuid)

        msg_id = message_dict[uuid]["id"]

        if contact_id is not None: save_msg(contact_id, message_dict, msg_id)
        else: save_msg(uuid, message_dict, msg_id)

        if not skip_check and self.currently_opened_chat != uuid:
            if self.chats.get(uuid) is None: 
                self.chats[uuid] = ui.SimpleFocusListWalker([])

        else:
            self.message_list.append(self.draw_message(sender, content))
            self.message_list.set_focus(len(self.message_list)-1)
            if contact_id is not None:
                self.message_ids[contact_id].add(msg_id)
            else: self.message_ids[uuid].add(msg_id)

        if self.currently_opened_chat == uuid:
            if contact_id is not None:
                self.save_chat(contact_id)
            else:
                self.save_chat(uuid)

        if self.debug_mode:
            self.debug_dissector(self.message_list)


    #### This is used for getting messages from server.py!!!
    def callback(self, data: bytes) -> None:
        message = data.decode()
        message = json.loads(message)

        def msg_unpack(message):
            uuid = list(message.keys())[0]
            sender = message[uuid].get("sender")
            content = message[uuid].get("content")

            return sender, content, message

        def unpack_write(msg):
            sender, _, message_dict = msg_unpack(msg)
            uuid = list(message_dict.keys())[0]
            if self.current_contact_name is not None and uuid == self.currently_opened_chat:
                self.current_contact_name.set_text(sender)
            self.add_msgs(message_dict)

        if isinstance(message, list):
            for nested_msg in message:
                unpack_write(nested_msg)

        else: 
            unpack_write(message)

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

        buttons = ui.Pile([
            ui.Columns([
                ui.Text("Exit & Settings"),
                self.exit_button,
                self.debug_button,
                ]),

            ui.Divider("-"),

            ui.Columns([
                ui.Text("Chat stuff) "),
                self.chat_button,
                ]),

            ui.Divider("-"),
            ])
        from . import version

        main = ui.Frame(
                ui.LineBox(buttons),
                header=ui.Text("Welcome back to TermChat!:3"),
                footer=ui.LineBox(ui.Text(f"Version) {version}")),
                focus_part="body",
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

    def save_chat(self, uuid):
        self.chats[uuid] = ui.SimpleFocusListWalker(self.message_list)

    def draw_message_list(self, uuid):
        if self.messages.get(uuid) is None:
            return
        for message_metadata in self.messages.get(uuid):
            sender = message_metadata[uuid].get("sender")
            content = message_metadata[uuid].get("content")
            id = message_metadata[uuid].get("id")
            
            messages_by_id = self.message_ids.get(uuid)

            if messages_by_id is None or id not in messages_by_id:
                if self.message_ids.get(uuid) is None:
                    self.message_ids[uuid] = set()

                self.message_ids[uuid].add(id)
                message = self.draw_message(sender, content)

                self.message_list.append(message)
                self.message_list.set_focus(len(self.message_list)-1)

        self.save_chat(uuid)


    def draw_chatbox(self, button, uuid, name):
        new_chat = uuid
        if self.debug_mode:
            self.debug_dissect_type(name)
        """
        this is here because for some reason,
        the code hallucinates name into a ui.Button
        i have 0 idea how the fuck this happens or where,
        but the lines below below seems to fix it
        """
        if isinstance(name, ui.Button):
            name = name.get_label()

        if self.chats.get(uuid) is not None:
            self.message_list = self.chats.get(uuid)
            self.message_view.body = self.message_list

        else: 
            self.save_chat(self.currently_opened_chat)
            self.message_list.clear()

        self.currently_opened_chat = uuid
        if isinstance(self.current_contact_name, ui.Text):
            self.current_contact_name.set_text(name)
        else:
            self.current_contact_name = ui.Text(name)
        self.draw_message_list(uuid)
    
    def create_contact(self, contact_id, contact_name):
        if contact_id not in self.already_made_buttons:
            button = ui.Button(contact_name)
            if self.debug_mode:
                self.debug_dissect_type(contact_name)
            ui.connect_signal(button, "click", 
                              self.draw_chatbox, 
                              user_args=[contact_id, contact_name])

            self.already_made_buttons.add(contact_id)

            self.contact_list.append(button)

    def chat_menu(self, callback_method):

        text_box = ui.Edit(">>> ")
        text_box_draw = ui.Columns([
            ("weight", 3, text_box,),
            ("pack", self.back_button,),
            ])
        text_box_draw.focus_position = 0

        interface = self

        if self.currently_opened_chat is not None:
            uuid = self.currently_opened_chat
        else:
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
                        client_uuid = interface.main_obj.data["uuid"]
                        message_dict = {
                                    client_uuid: {
                                    "receiver": interface.main_obj.data["receiver"],
                                    "sender": interface.main_obj.data["sender"],
                                    "content": text_box.get_edit_text(),
                                    "uuid": client_uuid,
                                    "id": interface.main_obj.data["id"],
                                    }
                                }
                        interface.add_msgs(message_dict,
                                           skip_check=True,
                                           contact_id=interface.currently_opened_chat)
                        callback_method(message_dict)
                        text_box.set_edit_text("")


        def generate_buttons():
            for contact_id, stuff in self.messages.items():
                if contact_id != self.main_obj.data["uuid"]:
                    chat_len = len(stuff)
                    while True:
                        if stuff[chat_len].get(contact_id) is None:
                            if chat_len == 0: break
                            chat_len -= 1
                            continue
                        else:
                            contact_name = stuff[chat_len][contact_id].get("sender")
                            self.create_contact(contact_id, contact_name)
                            break

        generate_buttons()
        try:
            default_start = self.messages[uuid][-1]
            self.current_contact_name = ui.Text(default_start[uuid].get("sender"))
        except (KeyError, IndexError):
            self.current_contact_name = ui.Text("No chat currently open!")
        self.draw_chatbox("",uuid, self.current_contact_name.get_text()[0])
        self.currently_opened_chat = uuid

        menu = ui.Columns([
            ("given",30,self.contact_buttons,),
            Page(ui.LineBox(self.message_view),
                footer=text_box_draw,
                header=self.current_contact_name,
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
