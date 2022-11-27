import cmd, os, sys, json

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
    data: str = None
    password: str = None


    def do_load(self, file):
        'Load a given file'

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

        if not os.path.isfile(file):
            msg = "'{}' not found.".format(file)
            print(msg)
            return

        ext = os.path.splitext(file)[1].replace('.', '').lower()
        if not ext in ['mp3']:
            msg = "Extension '{}' is not supported.".format(ext)
            print(msg)
            return


        with open(file, 'rb') as f:
            byte = f.read(1)
            data = ''

            while byte.hex() not in ['49', '44', '33', 'FF', 'FB', 'F3', 'F2']:
                data += byte.decode('utf-8')
                byte = f.read(1)

        if not '<morlock>' in data or not '</morlock>' in data:
            data = ''
        else:
            while not data.startswith('<morlock>'):
                data = data[1:]

            while not data.endswith('</morlock>'):
                data = data[:-1]

            data = data.replace('<morlock>', '').replace('</morlock>', '')

            while not self.is_json(data) and data != '':
                data = data[1:]

        data = json.loads(data or DEFAULT_STR)
        if not self.is_valid(data):
            msg = 'The given file is possibly corrupted.'
            print(msg)
            return

        msg = "'{}' loaded successfully.".format(file)
        self.file = file
        self.data = data
        print(msg, data)

    def do_list(self, *args):
        if self.file is None:
            msg = 'No file is currently loaded. First, run `load [FILE]`'
            print(msg)
            return

        print(self.data)

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

    def is_json(self, txt: str) -> bool:
        try:
            json.loads(txt)
        except ValueError:
            return False

        return True

    def is_valid(self, data: dict) -> bool:
        for key in DEFAULT.keys():
            if not key in data:
                return False

        return True