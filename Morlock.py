import cmd, os, sys, json, bcrypt, shlex

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
    file: str = None
    content: dict = None
    password: str = None

    def __init__(self, file: str, content: dict, password: str) -> None:
        self.file = file
        self.content = content
        self.password = password


class MorlockCli(cmd.Cmd):
    intro = 'Welcome to morlock.\nType help or ? to list commands.\n'
    prompt = 'morlock> '

    loadedfiles: list[MorlockFile] = []
    activefile: MorlockFile = None
    content: dict = None
    password: str = None

    def do_load(self, files):
        'Load given file(s)'

        for file in shlex.split(files):
            print("Loading '{}'...".format(file))

            # If to-be-active file is already loaded
            if self.findmorlockfile(file) is not None:
                msg = "'{}' is already loaded. Maybe try `switch`?".format(file)
                print(msg)
                continue

            # If to-be-active file is already active
            if self.activefile is not None:
                msg = "'{}' is already the acitve file.".format(file)
                print(msg)
                continue

            # If the given file does not exist
            if not os.path.isfile(file):
                msg = "'{}' not found.".format(file)
                print(msg)
                continue

            # If the file's extension isn't .mp3
            ext = os.path.splitext(file)[1].replace('.', '').lower()
            if not ext in ['mp3']:
                msg = "Extension '{}' is not supported.".format(ext)
                print(msg)
                continue

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
                while not MorlockCli.isjson(content) and content != '':
                    content = content[1:]

            # If `morlock` content isn't JSON
            content = json.loads(content or DEFAULT_STR)
            if not MorlockCli.isvalid(content):
                msg = "'{}' is possibly corrupted.".format(file)
                print(msg)
                continue

            # If file is encrypted
            if content['password'] is not None:
                msg = "Type in password for '{}': ".format(file)
                password = input(msg)
                match = bcrypt.checkpw(password.encode('utf-8'), content['password'].encode('utf-8'))
                if not match:
                    msg = 'Incorrect password entered.'
                    print(msg)
                    continue
            else:
                password = None

            msg = "'{}' loaded successfully. Activate it with `activate {}`".format(file, file)
            morlockfile = MorlockFile(file, content, password)
            self.loadedfiles.append(morlockfile)
            print(msg)

    def do_unload(self, file):
        pass 

    def do_list(self, files):
        "Print data that's saved on file(s) - given or active"

        # If files were given
        if files != '':
            for file in shlex.split(files):
                morlockfile = self.findmorlockfile(file)
                if morlockfile is None:
                    msg = "'{}' is not currently loaded. First, load it with `load {}`".format(file, file)
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

    def do_activate(self, file):
        morlockfile = self.findmorlockfile(file)
        if morlockfile is None:
            msg = "'{}' is not currently loaded. First, load it with `load {}`".format(file, file)
            print(msg)
            return

        if self.activefile is None:
            self.activefile = morlockfile
            self.prompt = 'morlock({})> '.format(file)
            msg = "'{}' activated successfully.".format(file)
            print(msg)
        else:
            file = self.activefile.file
            msg = "'{}' is currently active. First, deactivate it with `deactivate {}`".format(file, file)
            pass

    def do_save(self, arg):
        pass

    def do_close(self, arg, discard=False):
        if discard:
            pass
        else:
            pass

    def do_EOF(self, _=None):
        print(sep='')
        return True

    def findmorlockfile(self, file: str) -> MorlockFile:
        for loadedfile in self.loadedfiles:
            if loadedfile.file == file:
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