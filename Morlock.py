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

    def do_load(self, file):
        'Load a given file'

        # If there's a already file loaded
        if self.activefile is not None:
            action = None
            msg = "'{}' is currently loaded. Would you like to s(w)itch acitve files, (s)ave and close the current file or (d)iscard changes [sd]? ".format(self.activefile)
            
            while action not in ['s', 'd', 'w']:
                action = input(msg)
            
            if action == 's':
                self.do_save(file)
                self.do_close(file)
                self.do_load(file)
            elif action == 'd':
                self.do_close(discard=True)
            elif action == 'w':
                self.do_switch(file)
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
            while not MorlockCli.isjson(content) and content != '':
                content = content[1:]

        # If `morlock` content isn't JSON
        content = json.loads(content or DEFAULT_STR)
        if not MorlockCli.isvalid(content):
            msg = 'The given file is possibly corrupted.'
            print(msg)
            return

        # If file is encrypted
        if content['password'] is not None:
            msg = "Type in content's password: "
            password = input(msg)
            match = bcrypt.checkpw(password.encode('utf-8'), content['password'].encode('utf-8'))
            if not match:
                msg = 'Incorrect password entered.'
                print(msg)
                return
        else:
            password = None

        morlockfile = MorlockFile(file, content, password)
        msg = "'{}' loaded successfully.".format(file)
        self.prompt = 'morlock ({})> '.format(file)
        self.loadedfiles.append(morlockfile)
        self.activefile = morlockfile
        print(msg)

    def do_list(self, arg):
        if self.activefile is None:
            msg = 'No file is currently loaded. First, run `load [FILE]`'
            print(msg)
            return

        content = json.dumps(self.activefile.content or {}, ensure_ascii=False, indent=4)
        print(content)

    def do_switch(self, file):
        pass

    def do_set(self, arg):
        print(arg)

    def do_unload(self, arg):
        pass 

    def do_save(self, arg):
        pass

    def do_close(self, arg, discard=False):
        if discard:
            pass
        else:
            pass

    def do_EOF(self, *args):
        print(sep='')
        return True

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