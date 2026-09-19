from Crypto.Util.Padding import unpad
from Crypto.Hash import HMAC, SHA256
from Crypto.Util.Padding import pad
from Crypto.Protocol import KDF
from Crypto.Cipher import AES
from base64 import b64encode
from base64 import b64decode
import secrets
import json
import hmac

class BadParameter(Exception):
    def __init__(self, message, errors=None):
        super().__init__(message)
        self.errors = errors

class BadCallOrder(Exception):
    def __init__(self, message=None, errors=None):
        super().__init__(message)
        self.errors = errors

class AlreadySavedUUID(Exception):
    def __init__(self, message=None, errors=None):
        super().__init__(message)
        self.errors = errors

class WeakEncryptor(Exception):
    def __init__(self,message=None, errors=None):
        super().__init__(message)
        self.errors = errors

class MessageCrypt:
    def __init__(self):
        # 3072 bit modp
        self.modp = """FFFFFFFF FFFFFFFF C90FDAA2 2168C234 C4C6628B 80DC1CD1
29024E08 8A67CC74 020BBEA6 3B139B22 514A0879 8E3404DD
EF9519B3 CD3A431B 302B0A6D F25F1437 4FE1356D 6D51C245
E485B576 625E7EC6 F44C42E9 A637ED6B 0BFF5CB6 F406B7ED
EE386BFB 5A899FA5 AE9F2411 7C4B1FE6 49286651 ECE45B3D
C2007CB8 A163BF05 98DA4836 1C55D39A 69163FA8 FD24CF5F
83655D23 DCA3AD96 1C62F356 208552BB 9ED52907 7096966D
670C354E 4ABC9804 F1746C08 CA18217C 32905E46 2E36CE3B
E39E772C 180E8603 9B2783A2 EC07A28F B5C55DF0 6F4C52C9
DE2BCBF6 95581718 3995497C EA956AE5 15D22618 98FA0510
15728E5A 8AAAC42D AD33170D 04507A33 A85521AB DF1CBA64
ECFB8504 58DBEF0A 8AEA7157 5D060C7D B3970F85 A6E1E4C7
ABF5AE8C DB0933D7 1E8C94E0 4A25619D CEE3D226 1AD2EE6B
F12FFA06 D98A0864 D8760273 3EC86A64 521F2B18 177B200C
BBE11757 7A615D6C 770988C0 BAD946E2 08E24FA0 74E5AB31
43DB5BFC E0FD108E 4B82D120 A93AD2CA FFFFFFFF FFFFFFFF"""
        self.prime_key = int(self.modp.replace(" ", "").replace("\n", ""), 16)
        self.generator = 2

        self.private_key = secrets.randbelow(self.prime_key - 3) + 2
        self.public_key = pow(self.generator, self.private_key, self.prime_key)

        self.shared_keys = dict()

    def simple_contact_signature(self, uuid, contact_public_key, force_save=False):
        secret_key = self.comp_shared_key(contact_public_key)
        if secret_key is None:
            if self.shared_keys.get(uuid) is None: pass
            elif "hmac_key" not in self.shared_keys[uuid].keys():
                del self.shared_keys[uuid]
            raise WeakEncryptor("BnuuyCrypt.simple_contact_signature got a unsecure public_key!")

        self.save_contact_key(uuid, contact_public_key, force_save=force_save)
        self.save_to_keys(uuid, secret_key, force_save=force_save)

    def simple_encrypt_msg(self, message, uuid, sender_uuid):
        if isinstance(message, dict):
            message = json.dumps(message)

        cipher_dict = self.msg_encrypt(message, uuid)
        ct_hash = self.msg_fingerprint(cipher_dict.get("ciphertext"),
                                       self.get_byte(cipher_dict.get("iv")),
                                       uuid)

        uuid_hash = self.msg_fingerprint(sender_uuid,
                                         self.get_byte(cipher_dict.get("iv")),
                                         uuid,)

        cipher_dict["ct_hash"] = ct_hash
        cipher_dict["uuid_hash"] = uuid_hash
        cipher_dict["uuid"] = sender_uuid

        return cipher_dict

    def get_byte(self, value):
        if isinstance(value, str):
            return value.encode("utf-8")

        elif isinstance(value, int):
            if value < 1: raise BadParameter(f"BnuuyCrypt.get_byte got {value}!\nExpected any number above 0")
            return value.to_bytes((value.bit_length()+7) // 8, "big")

        else:
            raise BadParameter(f"BnuuyCrypt.get_byte expected int or str, received {type(value)}",
                               errors={"received": type(value),
                                       "expected": (int, str)})

    def get_int(self, call_site, value):
        if isinstance(value, str):
            value = value.encode()
        if isinstance(value, bytes):
            return int.from_bytes(value, "big")
        if isinstance(value, int):
            return value
        else:
            raise BadParameter(f"""{call_site} expected int, bytes or str
Received: {type(value)}""",
                    errors={"received": type(value),
                            "expected": (int, bytes, str)})

    def save_to_keys(self, uuid, shared_key, force_save=False):
        # note: shared key should be the shared secret key
        try:
            if "hmac_key" in self.shared_keys[uuid].keys(): 
                if not force_save: raise AlreadySavedUUID("UUID already saved! Call with force_save if you'd like to save anyway.")
            shared_secret_bytes = self.get_byte(shared_key)
            combined_key = self.public_key + self.shared_keys[uuid]["public_key"]
        except KeyError:
            raise BadCallOrder("""Entered UUID hasn't been saved! Please use
"BnuuyCrypt.save_contact_key(uuid, contact_public_key)"
before using BnuuyCrypt.save_to_keys""")

        combined_key_bytes = self.get_byte(combined_key)
        mac_key, enc_key = KDF.HKDF(shared_secret_bytes,
                                    32,
                                    combined_key_bytes,
                                    SHA256,
                                    2)

        self.shared_keys[uuid]["shared_key_bytes"] = shared_secret_bytes
        self.shared_keys[uuid]["shared_key_reg"] = shared_key
        self.shared_keys[uuid]["encrypt_key"] = enc_key
        self.shared_keys[uuid]["hmac_key"] = mac_key

    def save_contact_key(self, uuid, contact_public_key, force_save=False):
        # note, should be ran before self.save_to_keys
        contact_public_key = self.get_int("BnuuyCrypt.save_contact_key", contact_public_key)

        if self.shared_keys.get(uuid) is None:
            self.shared_keys[uuid] = {"public_key": contact_public_key}
        else:
            if not force_save:
                raise AlreadySavedUUID("""UUID has already been saved.
You can ovwrride this by adding force_save=True in the call""")
            else: self.shared_keys[uuid] = {"public_key": contact_public_key}

    def msg_fingerprint(self, message, iv, uuid, special_key=None, salt=None):
        """IMPORTANT NOTE!! this is to be used AFTER encryption and AFTER save_to_keys!!!"""
        if isinstance(message, str):
            message = self.get_byte(message)
        if special_key is None:
            try: 
                key_dict = self.shared_keys[uuid]
            except KeyError: raise BadCallOrder("""Entered UUID hasn't been saved! Please use MessageCrypt.simple_contact_signature""")

            try: key = key_dict["hmac_key"]
            except KeyError:
                raise BadCallOrder("Key 'hmac_key' doesnt exist in self.shared_keys, please call MessageCrypt.save_to_keys before BnuuyCrypt.msg_fingerprint!")


        else: 
            if not isinstance(special_key, bytes):
                special_key = self.get_byte(special_key)
            if not isinstance(salt, bytes):
                salt = self.get_byte(salt)

            key = KDF.scrypt(special_key, salt, 16, N=2**16, r=9, p=2)

        try: hash = HMAC.new(key, msg=message+iv, digestmod=SHA256)
        except TypeError:
            raise BadParameter("BnuuyCrypt.msg_fingerprint expected Bytes or str!")

        return hash.hexdigest()

    def msg_encrypt(self, message, uuid):
        try: key_dict = self.shared_keys[uuid]
        except KeyError:
            raise BadCallOrder("UUID has not been saved by BnuuyCrypt yet!")

        try: key = key_dict["encrypt_key"]
        except KeyError:
            raise BadCallOrder("Entered UUID hasn't been properly saved! Please call BnuuyCrypt.save_to_keys")

        message = self.get_byte(message)
        cipher = AES.new(key, AES.MODE_CBC)
        ct_bytes = cipher.encrypt(pad(message, AES.block_size))
        iv = b64encode(cipher.iv).decode('utf-8')
        ct = b64encode(ct_bytes).decode('utf-8')
        return {'iv':iv, 'ciphertext':ct}

    def msg_decrypt(self, message, uuid, return_bytes=False):
        try: key_dict = self.shared_keys[uuid]
        except KeyError:
            raise BadCallOrder("UUID is unsaved! Please call BnuuyCrypt.simple_contact_signature")
        try: enc_key = key_dict["encrypt_key"]
        except KeyError:
            raise BadCallOrder("UUID's information is incomplete! Please call BnuuyCrypt.save_to_keys")

        try:
            msg_dict = json.loads(message)
            hmac_key = self.shared_keys[uuid]["hmac_key"]
            iv_bytes = self.get_byte(msg_dict["iv"])
            ct_bytes = self.get_byte(msg_dict["ciphertext"])
            uuid_bytes = self.get_byte(msg_dict["uuid"])
            expected_ct_digest = HMAC.new(hmac_key,
                                          msg=ct_bytes+iv_bytes, 
                                          digestmod=SHA256).hexdigest()
            expected_uuid_digest = HMAC.new(hmac_key,
                                            msg=uuid_bytes+iv_bytes,
                                            digestmod=SHA256).hexdigest()

            ct_digest_check = hmac.compare_digest(expected_ct_digest,
                                                  msg_dict["ct_hash"])
            uuid_digest_check = hmac.compare_digest(expected_uuid_digest,
                                                    msg_dict["uuid_hash"])

            if not ct_digest_check or not uuid_digest_check:
                raise ValueError("HMAC hash doesnt match! Data was likely changed during transport.")

            iv = b64decode(msg_dict['iv'])
            ct = b64decode(msg_dict['ciphertext'])
            cipher = AES.new(enc_key, AES.MODE_CBC, iv)
            # msg dict but in bytes
            if return_bytes: return unpad(cipher.decrypt(ct), AES.block_size)
            # full decrypted msg dict
            decrypted_bytes = unpad(cipher.decrypt(ct), AES.block_size)
            return json.loads(decrypted_bytes)

        except (ValueError, KeyError, TypeError):
            raise BadParameter("Failed to decrypt!:(")

    def comp_shared_key(self, public_key):
        if not isinstance(public_key, int):
            public_key = self.get_int("BnuuyCrypt.comp_shared_key", public_key)

        if public_key in (0,1, self.prime_key-1):
            return None
        elif public_key >= self.prime_key or public_key < 0: 
            return None
        else:
            return pow(public_key, self.private_key, self.prime_key)



class RandGenerators:
    def __init__(self):
        pass

    def rand_key(self, wordlist_gen=False, wordlist_file=None, wordlist_len=4, key_bytes=32):
        if wordlist_gen:
            if wordlist_file is None: 
                raise BadParameter("RandGenerators.rand_key requires a filepath/file in the wordlist_file arg when using wordlist mode!")
            elif wordlist_len < 1:
                raise BadParameter(f"wordlist_len should be > 1, got {wordlist_len}")
            wordlist = []
            try:
                with open(wordlist_file) as f:
                    words = [word.strip() for word in f]
                    wordlist.extend(secrets.choice(words) for i in range(wordlist_len))
                    wordlist = [word.split("\t")[1] for word in wordlist]
                    return ' '.join(wordlist)

            except (IndexError,
                    OSError,
                    TypeError,
                    UnicodeDecodeError) as e:
                raise ValueError(f"An error occurred while reading {wordlist_file}: {e}")

        else:
            return secrets.token_urlsafe(key_bytes)
