from __future__ import annotations
import os
import sys
import json
import urwid as ui
from . import Server
import uuid as id_gen
from . import BnuuyCrypt
from time import gmtime, strftime, sleep
# fuck you annotations for breaking my import style

class Interface():
    def __init__(self, main_obj):
        self.main_obj = main_obj
        self.screen = ui.raw_display.Screen()
        self.write_fd = None
        self.loop = None
        self.main_menu_widget = None
        self.debug_mode = False

        #### BUTTON SECTION
        self.exit_button = ui.Button("Exit")
        self.chat_button = ui.Button("Open chat")
        self.add_friend_button = ui.Button("Add a new friend")
        self.back_button = ui.Button("Back")
        self.debug_button = ui.Button("Debug mode")
        self.gen_authkey_button = ui.Button("Generate a new one-time auth key")
        self.remove_contact_button = ui.Button("Remove this contact")
        self.block_contact_button = ui.Button("Block this contact")

        ui.connect_signal(self.exit_button, "click", self.stop_program)
        ui.connect_signal(self.chat_button, "click", self.main_obj.send_msg)
        ui.connect_signal(self.add_friend_button, "click", self.add_friend)
        ui.connect_signal(self.back_button, "click", self.go_to_mainmenu)
        ui.connect_signal(self.debug_button, "click", self.debug_switch)
        ui.connect_signal(self.gen_authkey_button, "click", self.authkey_gen)
        ui.connect_signal(self.remove_contact_button, "click", self.remove_friend)
        ui.connect_signal(self.block_contact_button, "click", self.block_friend)

        #### COLORS
        self.palette = [
                ("err", "white", "dark red"), # for errors
                ("clr_err", "default", "default"), # empty a row
                ("success", "white", "dark green"),
                ("lgrey_txt", "light gray", "default"),
                ("dgrey_txt", "dark gray", "default"),
                ("default", "default", "default")
                ]

        #### MESSAGES
        self.messages = dict()

        self.message_list = ui.SimpleFocusListWalker([])
        self.message_view = ui.ListBox(self.message_list)
        self.message_ids = dict()

        #### CONTACT BUTTON WIDGETS
        self.contact_list = ui.SimpleFocusListWalker([])
        self.contact_buttons = ui.ListBox(self.contact_list)
        self.already_made_buttons = dict()

        #### CHAT HANDLING
        #note: i am afraid this may take me a while :(((
        #current time: 27 Aug 2026, 12:34 AM
        self.chats = dict()
        self.contact_ips = dict()
        self.contact_info = dict()
        # note this shiuld always be a uuid
        self.currently_opened_chat = None
        # should always be urwid.Text
        self.current_contact_name = None
        # should be list of AttrMap
        self.currently_sending_msg = list()

        #### HANDSHAKE KEYS
        self.key_list = ui.SimpleFocusListWalker([])
        self.key_listbox = ui.ListBox(self.key_list)

        #### OTHER
        self.confirm_del = False
        self.authkeys_in_use = dict()

    def authkey_gen(self, button):
        try:
            wordlist_path = os.path.join(os.path.dirname(__file__), "eff_large_wordlist.txt")
            key = self.main_obj.rand_gen.rand_key(wordlist_gen=True,
                                               wordlist_file=wordlist_path)
            self.key_list.append(ui.Text(key))
        except ValueError:
            pass

    #### BLOCK HANDLING
    def blocked_contact_button_styler(self, uuid, unblock=False):
        if unblock: map = "default"
        else: map = "err"
        if isinstance(self.already_made_buttons[uuid][1], ui.AttrMap):
            self.already_made_buttons[uuid][1].set_attr_map({None: map})
            contact_button = self.already_made_buttons[uuid][1]
        else:
            contact_button = ui.AttrMap(self.already_made_buttons[uuid][1], map)
        return contact_button

    def block_contact(self, uuid):
        if uuid == self.main_obj.data["uuid"]: return None
        def find_uuid_pos(contact_button, name):
            pos = 0
            for key in self.already_made_buttons.keys():
                if key == uuid:
                    if isinstance(self.contact_list[pos], ui.AttrMap):
                        self.contact_list[pos].original_widget.set_label(name)
                    else: self.contact_list[pos].set_label(name)
                    self.contact_list[pos] = contact_button
                    self.already_made_buttons[uuid][1] = contact_button
                    return None
                else: pos += 1

        if self.contact_info[uuid]["block_status"] is False:
            self.contact_info[uuid]["block_status"] = True
            name = f"(BLOCKED) {self.already_made_buttons[uuid][0]}"
            find_uuid_pos(self.blocked_contact_button_styler(uuid), name)
            self.block_contact_button.set_label("Unblock this contact")
            return None

        self.contact_info[uuid]["block_status"] = False
        name = self.contact_info[uuid]["name"]
        find_uuid_pos(self.blocked_contact_button_styler(uuid, unblock=True), name)
        self.block_contact_button.set_label("Block this contact")

    #### RWMOVE HANDLING
    def del_contact(self, uuid):
        if uuid == self.main_obj.data["uuid"]: return None
        if uuid not in self.messages: return None
        to_be_deleted_from = [self.contact_ips,
                              self.messages, 
                              self.message_ids,
                              self.main_obj.msg_crypt.shared_keys,
                              self.contact_info,
                              self.chats]
        for storage in to_be_deleted_from:
            try: del storage[uuid]
            except KeyError: continue

        self.already_made_buttons.clear()
        if uuid == self.currently_opened_chat:
            self.currently_opened_chat = self.main_obj.data["uuid"]
            self.current_contact_name.set_text("No chat currently open!")
            self.draw_chatbox(self.currently_opened_chat, 
                              self.current_contact_name.get_text()[0], "")


        self.contact_list.clear()
        self.generate_buttons()
        self.loop.draw_screen()

    def remove_friend(self, button):
        if self.confirm_del is False:
            self.remove_contact_button.set_label("Are you sure?")
            self.confirm_del = True
            return
        else:
            self.confirm_del = False
            self.remove_contact_button.set_label("Remove this contact")
            self.del_contact(self.currently_opened_chat)

    def block_friend(self, button):
        self.block_contact(self.currently_opened_chat)

    def add_friend(self, button):
        contact_ip = ui.Edit(">>> ")
        contact_authkey = ui.Edit(">>> ")
        status = ui.Text("", align="center")
        status_map = ui.AttrMap(status, "clr_err")
        interface = self
        page_copy = None

        menu = ui.Pile([
            ui.Text("Your auth keys", align="center"),
            ui.BoxAdapter(ui.LineBox(self.key_listbox), 15),
            ui.Divider("-"),
            ui.Text("Please enter the contact's IP or DNS."),
            contact_ip,
            ui.Divider("-"),
            ui.Text("Enter the contact's auth key. (not your own!)"),
            contact_authkey,
            ui.Divider("-"),
            ])

        buttons = ui.Columns([
            self.back_button,
            self.gen_authkey_button,
            ])

        class Page(ui.Frame):
            def upd_status(self, txt, map):
                status.set_text(txt)
                status_map.set_attr_map({None: map})

            def keypress(self, size, key):
                if page_copy.focus_part == "footer" or key != "enter":
                    return super().keypress(size, key)

                
                self.upd_status("Attempting connection.. Please wait!", "default")
                interface.loop.draw_screen()
                info = {
                    "link": contact_ip,
                    "authkey": contact_authkey,
                    "status": status,
                    "status_map": status_map,
                    "page_class": self,
                    "interface": interface,
                    }
                Server.friend_handshake(info)

        form = Page(ui.LineBox(menu),
                        header=status_map,
                        footer=ui.LineBox(buttons),
                        focus_part="body")
        page_copy = form

        if self.loop is None: self.run_menu(form)
        else: self.loop.widget = form

    def go_to_mainmenu(self, button):
        self.loop.widget = self.main_menu_widget

    def debug_switch(self, button):
        self.debug_mode = not self.debug_mode
        self.debug_button.set_label(f"Debug mode ({self.debug_mode})")

    def debug_dissector(self, value):
        if self.loop is not None:
            self.loop.stop()
        print(value)
        input("Enter any key to continue the code: ")
        if self.loop is not None:
            self.loop.start()

    def debug_dissect_type(self, value):
        if self.loop is not None:
            self.loop.stop()
        print(type(value), value)
        input("Enter any key to continue the code: ")
        if self.loop is not None:
            self.loop.start()

    #def add_msgs(self, message_dict, skip_check=False, contact_id=None):
        # rewworked this method into the one below
        # yipee :3 completed (oct 2 2026)
        # this one method caused me so much annoyance btw, never write code like this
        # NOTE: A contact_id should be passed!!
    #    if contact_id is None: return None
    #    if not isinstance(message_dict[uuid]["id"], str): return None
    #    try:
    #        uuid = contact_id
    #        sender = message_dict[uuid]["sender"]
    #        content = message_dict[uuid]["content"]
    #        if "id" not in message_dict[uuid].keys(): raise KeyError
    #    except (KeyError, AttributeError, IndexError, TypeError): return None
        # i gave up all pretense of clean code whilst making this method

    #    def init_message_db(uid):
    #        self.message_ids[uid] = set()
    #        self.messages[uid] = []

    #    def save_msg(uid, message_dict, msg_id):
    #       self.messages[uid].append(message_dict)

    #    if contact_id is not None and self.messages.get(contact_id) is None:
    #        if uuid != self.main_obj.data["uuid"]:
    #            self.create_contact(contact_id, sender)
    #       init_message_db(contact_id)

    #    msg_id = message_dict[uuid]["id"]
    #    if msg_id in self.message_ids[contact_id]: return None

    #   save_msg(contact_id, message_dict, msg_id)
        #self.message_tracker.append((msg_id, len(self.messages[contact_id])-1))

    #    if not skip_check and self.currently_opened_chat != uuid:
    #        if self.chats.get(uuid) is None: 
    #            self.chats[uuid] = ui.SimpleFocusListWalker([])

    #    else:
    #        self.message_list.append(self.draw_message(sender, content, message_dict[uuid].get("time_sent")))

    #        if uuid == self.main_obj.data["uuid"]:
    #           self.message_list[-1] = ui.AttrMap(self.message_list[-1], "dgrey_txt")
    #           self.currently_sending_msg.append(self.message_list[-1])

    #        self.message_list.set_focus(len(self.message_list)-1)
    #        if contact_id is not None and msg_id not in self.message_ids[contact_id]:
    #            self.message_ids[contact_id].add(msg_id)

    #    if self.currently_opened_chat == contact_id:
    #        if contact_id is not None:
    #            self.save_chat(contact_id)

    #    if self.debug_mode:
    #        self.debug_dissector(self.message_list)

    def add_msgs(self, message_dict, sending=False, contact_id=None):
        if sending: msg_uuid = self.main_obj.data["uuid"]
        else: msg_uuid = contact_id
        try:
            if not isinstance(message_dict[msg_uuid]["id"], str): raise KeyError
            sender = message_dict[msg_uuid]["sender"]
            content = message_dict[msg_uuid]["content"]
            msg_id = message_dict[msg_uuid]["id"]
        except (KeyError, AttributeError, IndexError, TypeError): return None
        if self.messages.get(contact_id) is None: return None
        if msg_id in self.message_ids[contact_id]: return None

        self.messages[contact_id].append(message_dict)
        self.message_ids[contact_id].add(msg_id)
        if self.currently_opened_chat == contact_id or sending:
            self.message_list.append(self.draw_message(sender,
                                               content,
                                               message_dict[msg_uuid].get("time_sent")))
            self.message_list.set_focus(len(self.message_list)-1)

        if sending:
            self.message_list[-1] = ui.AttrMap(self.message_list[-1], "dgrey_txt")
            self.currently_sending_msg.append(self.message_list[-1])

        if self.currently_opened_chat == contact_id:
            self.save_chat(contact_id)
        return "all good :3"

    #### This is used for getting messages from server.py!!!
    def callback(self, data: bytes) -> None:
        try:
            message = data.decode()
            message = json.loads(message)
        except json.JSONDecodeError:
            return None

        if isinstance(message, dict) and "save_new_contact" in message.keys():
            ip, uuid, name = message["save_new_contact"]
            if isinstance(name, str) and isinstance(ip, str) and isinstance(uuid, str) and uuid not in self.messages:
                self.contact_ips[uuid] = ip
                self.message_ids[uuid] = set()
                self.messages[uuid] = []
                self.create_contact(uuid, name)
                self.contact_info[uuid] = {"name": name,
                                           "uuid": uuid,
                                           "ip": ip,
                                           "block_status": False,}
                self.loop.draw_screen()
            return None 

        def msg_unpack(message, uuid):
            try:
                #uuid = list(message.keys())[0]
                sender = message[uuid].get("sender")
                #content = message[uuid].get("content")
            except (KeyError, IndexError, AttributeError, TypeError): return None

            return sender

        def unpack_write(msg, uuid):
            sender = msg_unpack(msg, uuid)
            if sender is None: return None
            if not isinstance(sender, str):
                sender = "Name couldnt be rendered!"

            if self.current_contact_name is not None and uuid == self.currently_opened_chat:
                if self.current_contact_name.get_text()[0] != sender:
                    self.current_contact_name.set_text(sender)

            self.add_msgs(msg, contact_id=uuid)

        def prep_msg(message):
            return message.get("uuid"), message.get("pub_key")

        if isinstance(message, list):
            for nested_msg in message:
                uuid, _ = prep_msg(nested_msg)
                if uuid in self.contact_info and self.contact_info[uuid].get("block_status") is True:
                    continue
                try: nested_msg = self.main_obj.msg_crypt.msg_decrypt(nested_msg, uuid)
                except (BnuuyCrypt.BadCallOrder, BnuuyCrypt.BadParameter):
                    # note, this should be updated to make a popup with a warning
                    continue
                unpack_write(nested_msg, uuid)

        else:
            uuid, _ = prep_msg(message)

            if uuid in self.contact_info and self.contact_info[uuid].get("block_status") is True:
                return None
            try: message = self.main_obj.msg_crypt.msg_decrypt(message, uuid)
            except (BnuuyCrypt.BadCallOrder, BnuuyCrypt.BadParameter):
                # same as above
                return None

            unpack_write(message, uuid)

        if self.loop is not None: self.loop.draw_screen()


    def run_menu(self, menu, u_input=None):

        if u_input is not None:
            self.loop = ui.MainLoop(menu, self.palette, 
                                    unhandled_input=u_input, screen=self.screen)
        else:
            self.loop = ui.MainLoop(menu, self.palette, screen=self.screen)
        self.write_fd = self.loop.watch_pipe(self.callback)
        self.loop.run()

        while self.main_obj.sending_post: sleep(0.10)
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
        page_copy = None

        class Page(ui.Frame):

            def keypress(self, size, key):
                if page_copy.focus_part == "footer" or key != "enter":
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
            ui.LineBox(ui.Text("""Welcome to InvisiChat! :3
To continue, please fill these fields
(Note: Your DNS/IP and password are stored on-device and encrypted.)(password handling not yet implemented)""")),

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
        page_copy = login
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
                self.add_friend_button,
                ]),

            ui.Divider("-"),
            ])
        from . import version

        main = ui.Frame(
                ui.LineBox(buttons),
                header=ui.Text("Welcome back to InvisiChat!:3"),
                footer=ui.LineBox(ui.Text(f"Version) {version}")),
                focus_part="body",
                )
        self.main_menu_widget = main
        if self.loop is None:
            self.run_menu(main)
        else:
            self.loop.widget = main

    def draw_message(self, sender, content, time_sent):
        if not isinstance(sender, str):
            sender = "Name couldnt be rendered! The peer sent an invalid name type!"
        if not isinstance(content, str):
            content = "Message couldnt be rendered! The peer sent an invalid message type!"
        if not isinstance(time_sent, str):
            time_sent = "Time couldnt be rendered!"
        message = ui.Pile([
                ui.Divider("-"),
                ui.Text(f"{sender})"),
                ui.Text(content),
                ui.Divider("-"),
                ui.Text(time_sent),
                ui.Divider("-"),
            ])
        return message

    def save_chat(self, uuid):
        self.chats[uuid] = ui.SimpleFocusListWalker(self.message_list)

    def draw_message_list(self, uuid):
        if self.messages.get(uuid) is None:
            return
        self.message_list.clear()
        for message_metadata in self.messages.get(uuid):
            if message_metadata.get(uuid) is None: sender_uuid = self.main_obj.data["uuid"]
            else: sender_uuid = uuid
            try:
                sender = message_metadata[sender_uuid].get("sender")
                content = message_metadata[sender_uuid].get("content")
                time_sent = message_metadata[sender_uuid].get("time_sent")
                send_status = message_metadata[sender_uuid].get("failed_send")
            except (KeyError, AttributeError): continue

            message = self.draw_message(sender, content, time_sent)
            if send_status:
                message = ui.AttrMap(message, "err")

            self.message_list.append(message)
            self.message_list.set_focus(len(self.message_list)-1)

        self.save_chat(uuid)


    def draw_chatbox(self, uuid, name, button):
        client_uuid = self.main_obj.data["uuid"]
        curr_chat = self.currently_opened_chat
        if self.debug_mode:
            self.debug_dissect_type(name)

        if curr_chat == client_uuid:
            # no chat open case
            self.message_list.clear()

        elif self.chats.get(uuid) is not None:
            # opening new chat
            if curr_chat is not None:
                self.save_chat(self.currently_opened_chat)
            self.message_list = self.chats.get(uuid)
            self.message_view.body = self.message_list

        else:
            if curr_chat is not None:
                self.save_chat(self.currently_opened_chat)
                self.message_list.clear()

        self.currently_opened_chat = uuid
        if isinstance(self.current_contact_name, ui.Text):
            self.current_contact_name.set_text(name)
        else:
            self.current_contact_name = ui.Text(name, align="center")

        if uuid != self.main_obj.data["uuid"] and self.contact_info[uuid]["block_status"]:
            self.block_contact_button.set_label("Unblock this contact")
        else:
            self.block_contact_button.set_label("Block this contact")

        if self.confirm_del:
            self.confirm_del = False
            self.remove_contact_button.set_label("Remove this contact")
        self.draw_message_list(uuid)
    
    def create_contact(self, contact_id, contact_name):
        if contact_id not in self.already_made_buttons.keys():
            button = ui.Button(contact_name)
            if self.debug_mode:
                self.debug_dissect_type(contact_name)
            ui.connect_signal(button, "click", 
                              self.draw_chatbox, 
                              user_args=[contact_id, contact_name])

            self.already_made_buttons[contact_id] = [contact_name, button]

            self.contact_list.append(button)

    def generate_buttons(self):
        pos = 0
        for contact_id, stuff in self.messages.items():
            if contact_id != self.main_obj.data["uuid"] and contact_id in self.contact_info:
                contact_name = self.contact_info[contact_id].get("name")
                if not isinstance(contact_name, str): continue
                self.create_contact(contact_id, contact_name)

                if self.contact_info[contact_id]["block_status"]:
                    name = self.already_made_buttons[contact_id][0]

                    if isinstance(self.already_made_buttons[contact_id][1], ui.AttrMap):
                        self.already_made_buttons[contact_id][1].set_attr_map({None: "err"})
                        self.already_made_buttons[contact_id][1].original_widget.set_label(f"(BLOCKED) {name}")
                    else:
                        self.already_made_buttons[contact_id][1].set_label(f"(BLOCKED) {name}")
                        button = self.already_made_buttons[contact_id][1]
                        self.already_made_buttons[contact_id][1] = ui.AttrMap(button, "err")
                    self.contact_list[pos] = self.already_made_buttons[contact_id][1]
            else: continue

            pos += 1

    def chat_menu(self, callback_method):

        text_box = ui.Edit(">>> ")
        text_box_draw = ui.Columns([
            text_box,
            ])
        text_box_draw.focus_position = 0
        frame_copy = None
        interface = self

        if self.currently_opened_chat is not None:
            uuid = self.currently_opened_chat
        else:
            uuid = self.main_obj.data["uuid"]

        class Page(ui.Frame):
            def keypress(self, size, key):
                if key != "enter" or frame_copy.focus_part != "footer":
                    return super().keypress(size, key)

                curr_chat = interface.currently_opened_chat
                if len(text_box.get_edit_text()) >= 1:
                    text = text_box.get_edit_text()
                    if curr_chat == interface.main_obj.data["uuid"]:
                        return None
                    if interface.contact_info[curr_chat].get("block_status"):
                        return None
                    text_box.set_edit_text("")
                    interface.main_obj.data["id"] = str(id_gen.uuid4())
                    client_uuid = interface.main_obj.data["uuid"]
                    message_dict = {
                                client_uuid: {
                                "failed_send": False,
                                "receiver": interface.main_obj.data["receiver"],
                                "time_sent": strftime("%Y-%m-%d %H:%M:%S", gmtime()),
                                "sender": interface.main_obj.data["sender"],
                                "content": text,
                                "uuid": client_uuid,
                                "id": interface.main_obj.data["id"],
                                }
                            }
                    res = interface.add_msgs(message_dict,
                                       sending=True,
                                       contact_id=interface.currently_opened_chat)
                    if res is None: return None
                    pos = len(interface.currently_sending_msg)-1
                    callback_method(message_dict, pos)

        self.generate_buttons()
        if self.currently_opened_chat is not None and self.currently_opened_chat != self.main_obj.data["uuid"]:
            self.current_contact_name = ui.Text(
                    self.already_made_buttons[self.currently_opened_chat][0],
                    align="center"
                    )

            self.draw_chatbox(uuid, self.current_contact_name.get_text()[0], "")

        else:
            self.current_contact_name = ui.Text("No chat currently open!", align="center")
            self.draw_chatbox(uuid, self.current_contact_name.get_text()[0], "")

        header = ui.Pile([
            ui.Columns([
                self.back_button,
                ("pack", self.remove_contact_button),
                ("pack", self.block_contact_button),
                ]),
            self.current_contact_name,
            ])
        chat_frame = Page(ui.LineBox(self.message_view),
                footer=text_box_draw,
                header=header,
                focus_part="footer")
        frame_copy = chat_frame
        menu = ui.Columns([
            ("given",20,ui.LineBox(self.contact_buttons),),
            chat_frame,
            ])
        menu.focus_position = 1
        if self.loop is None:
            self.run_menu(menu)
        else: self.loop.widget = menu
