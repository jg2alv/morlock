import cmd, os, json, bcrypt, shlex

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

class MorlockFile:
    path: str = None
    content: dict = None
    password: str = None
    modified: bool = False

    def __init__(self, path: str, content: dict, password: str) -> None:
        self.path = path
        self.content = content
        self.password = password


class MorlockCli(cmd.Cmd):
    intro = 'Welcome to morlock.\nType help or ? to list commands.\n'
    prompt = 'morlock> '

    loadedfiles: list[MorlockFile] = []
    activefile: MorlockFile = None
    content: dict = None
    password: str = None

    def do_load(self, paths):
        'Load given file(s)'

        for path in shlex.split(paths):
            print("Loading '{}'...".format(path))

            # If to-be-active file is already loaded
            if self.findmorlockfile(path) is not None:
                msg = "'{}' is already loaded. Maybe try `switch`?".format(path)
                print(msg)
                continue

            # If to-be-active file is already active
            if self.activefile is not None:
                msg = "'{}' is already the acitve file.".format(path)
                print(msg)
                continue

            # If the given file does not exist
            if not os.path.isfile(path):
                msg = "'{}' not found.".format(path)
                print(msg)
                continue

            # If the file's extension isn't .mp3
            ext = os.path.splitext(path)[1].replace('.', '').lower()
            if not ext in ['mp3']:
                msg = "Extension '{}' is not supported.".format(ext)
                print(msg)
                continue

            with open(path, 'rb') as f:
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
                while not MorlockCli.isjson(content) and content != '':
                    content = content[1:]

            # If `morlock` content isn't JSON
            content = json.loads(content or DEFAULT_STR)
            if not MorlockCli.isvalid(content):
                msg = "'{}' is possibly corrupted.".format(path)
                print(msg)
                continue

            # If file is encrypted
            if content['password'] is not None:
                msg = "Type in password for '{}': ".format(path)
                password = input(msg)
                match = bcrypt.checkpw(password.encode('utf-8'), content['password'].encode('utf-8'))
                if not match:
                    msg = 'Incorrect password entered.'
                    print(msg)
                    continue
            else:
                password = None

            msg = "'{}' loaded successfully. Activate it with `activate {}`".format(path, path)
            morlockfile = MorlockFile(path, content, password)
            self.loadedfiles.append(morlockfile)
            print(msg)

    def do_unload(self, paths):
        for path in shlex.split(paths):
            morlockfile = self.findmorlockfile(path)
            if morlockfile is None:
                msg = "'{}' is not currently loaded. First, load it with `load {}`".format(path, path)
                print(msg)
                continue

            if morlockfile.modified:
                msg = "'{}' was modified. Do you wish to close it and discard changes (y/n)? ".format(path)
                discard = input(msg)

                while discard.lower() not in ['y', 'n']:
                    discard = input(msg)

                if discard == 'n':
                    continue
            
            if self.activefile == morlockfile:
                self.do_deactivate()

            msg = "'{}' successfully closed.".format(path)
            self.loadedfiles.remove(morlockfile)
            print(msg)

    def do_list(self, paths):
        "Print data that's saved on file(s) - given or active"

        # If files were given
        if paths != '':
            for path in shlex.split(paths):
                morlockfile = self.findmorlockfile(path)
                if morlockfile is None:
                    msg = "'{}' is not currently loaded. First, load it with `load {}`".format(path, path)
                    print(msg)
                    continue
                
                content = json.dumps(morlockfile.content or {}, ensure_ascii=False, indent=4)
                print(content)

            return
        
        if self.activefile is None:
            msg = 'No file is currently active. First, run `activate [FILE]`'
            print(msg)
            return

        content = json.dumps(self.activefile.content or {}, ensure_ascii=False, indent=4)
        print(content)

    def do_set(self, arg):
        print(arg)

    def do_activate(self, path):
        morlockfile = self.findmorlockfile(path)
        if morlockfile is None:
            msg = "'{}' is not currently loaded. First, load it with `load {}`".format(path, path)
            print(msg)
            return

        if self.activefile is None:
            self.activefile = morlockfile
            self.prompt = 'morlock({})> '.format(path)
            msg = "'{}' activated successfully.".format(path)
            print(msg)
        else:
            path = self.activefile.path
            msg = "'{}' is currently active. First, deactivate it with `deactivate {}`".format(path, path)
            pass

    def do_deactivate(self, _: str=None):
        if self.activefile is None:
            msg = "There's no currently active file."
            print(msg)
            return

        self.activefile = None
        self.prompt = 'morlock> '

    def do_switch(self, path: str) -> None:
        '`switch [FILE]` is a shortcut for `deactivate; activate [FILE]`'

        morlockfile = self.findmorlockfile(path)

        # If to-be-active file is not loaded
        if morlockfile is None:
            msg = "'{}' is not loaded. Run `load {}` first".format(path, path)
            print(msg)
        else:
            if self.activefile is not None:
                self.do_deactivate()
            
            self.do_activate(path)

    def do_save(self, arg):
        pass

    def do_EOF(self, _=None):
        print(sep='')
        return True

    def findmorlockfile(self, path: str) -> MorlockFile:
        for loadedfile in self.loadedfiles:
            if loadedfile.path == path:
                return loadedfile

        return None

    @staticmethod
    def isjson(txt: str) -> bool:
        try:
            json.loads(txt)
        except ValueError:
            return False

        return True

    @staticmethod
    def isvalid(content: dict) -> bool:
        for key in DEFAULT.keys():
            if not key in content:
                return False

        return True