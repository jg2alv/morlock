import cmd, os, sys, json, bcrypt

DEFAULT = {
    "name": "[unnamed]",
    "password": None,
    "data": {}
}
DEFAULT_STR = str(DEFAULT)

"""
    {
        "name": "anakarine",
        "data": {

        }
    }
"""

class Morlock(cmd.Cmd):
    intro = 'Welcome to morlock.\nType help or ? to list commands.\n'
    prompt = 'morlock> '

    file: str = None
    content: dict = None
    password: str = None

    def do_load(self, file):
        'Load a given file'

        # If there's a already file loaded
        if self.file is not None:
            action = None
            msg = "'{}' is currently loaded. Would you like to (s)ave and close the current file or (d)iscard changes [sd]? ".format(self.file)
            
            while action not in ['s', 'd']:
                action = input(msg)
            
            if action == 's':
                self.do_save(file)
                self.do_close(file)
                self.do_load(file)
            elif action == 'd':
                self.do_close(discard=True)
            else:
                msg = 'Something went terribly wrong - exiting...'
                print(msg)
                sys.exit(1)

            return

        # If the given file does not exist
        if not os.path.isfile(file):
            msg = "'{}' not found.".format(file)
            print(msg)
            return

        # If the file's extension isn't .mp3
        ext = os.path.splitext(file)[1].replace('.', '').lower()
        if not ext in ['mp3']:
            msg = "Extension '{}' is not supported.".format(ext)
            print(msg)
            return

        with open(file, 'rb') as f:
            byte = f.read()
            content = []

            # Reading until the start of MP3 content
            while not byte.startswith(b'ID3'):
                content.append(byte[0])
                byte = byte[1:] 

            # Turning array of ints into string with `morlock` content
            content = "".join(map(chr, content))

        # Getting `morlock` content inside of the file's head
        if not '<morlock>' in content or not '</morlock>' in content:
            content = ''
        else:
            while not content.startswith('<morlock>'):
                content = content[1:]

            while not content.endswith('</morlock>'):
                content = content[:-1]

            # Removing `morlock` tags
            content = content.replace('<morlock>', '').replace('</morlock>', '')

            # Extracting JSON content
            while not Morlock.is_json(content) and content != '':
                content = content[1:]

        content = json.loads(content or DEFAULT_STR)
        # If `morlock` content isn't JSON
        if not Morlock.is_valid(content):
            msg = 'The given file is possibly corrupted.'
            print(msg)
            return

        # If file is encrypted
        if content['password'] is not None:
            msg = "Type in content's password: "
            self.password = self.password or input(msg)
            match = bcrypt.checkpw(self.password.encode('utf-8'), content['password'].encode('utf-8'))
            if not match:
                msg = 'Incorrect password entered.'
                print(msg)
                return

        msg = "'{}' loaded successfully.".format(file)
        self.file = file
        self.content = content
        print(msg)

    def do_list(self, *args):
        if self.file is None:
            msg = 'No file is currently loaded. First, run `load [FILE]`'
            print(msg)
            return

        content = json.dumps(self.content or {}, ensure_ascii=False, indent=4)
        print(content)

    def do_unload(self, *args):
        pass 

    def do_save(self, *args):
        pass

    def do_close(self, *args, discard=False):
        if discard:
            pass
        else:
            pass

    def do_EOF(self, *args):
        print(sep='')
        return True

    def set_file(self, file=None):
        if file is not None:
            self.file = file

    def set_password(self, password=None):
        if password is not None:
            self.password = password

    @staticmethod
    def is_json(txt: str) -> bool:
        try:
            json.loads(txt)
        except ValueError:
            return False

        return True

    @staticmethod
    def is_valid(content: dict) -> bool:
        for key in DEFAULT.keys():
            if not key in content:
                return False

        return True