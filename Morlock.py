import cmd, os, json, bcrypt, shlex, re, copy

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

    def do_load(self, paths: str) -> None:
        'Load given file(s)'

        for path in shlex.split(paths):
            print("Loading '{}'...".format(path))

            # If to-be-active file is already loaded
            if self.findmorlockfile({'path': path}) is not None:
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

    def do_unload(self, paths: str) -> None:
        for path in shlex.split(paths):
            morlockfile = self.findmorlockfile({'path': path})
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

    def do_list(self, paths: str) -> None:
        "Print data that's saved on file(s) - given or active"

        # If files were given
        if paths != '':
            for path in shlex.split(paths):
                morlockfile = self.findmorlockfile({'path': path})
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

    def do_set(self, args: str) -> None:
        """Set content of active file.
        Syntax: `set key val`
        The command takes exactly two arguments.
        `key` must include only {a-z,.,0-9,A-Z,],[} characters.
        In order to access a sublevel, enter level1.level2 like syntax: `set first_level.second_level.third_level value`
        """

        args = shlex.split(args)

        # Exactly two arguments are accepted.
        if len(args) != 2:
            msg = 'Invalid syntax. See `help set`.'
            print(msg)
            return

        # The only file that can be modified is the active one
        if self.activefile is None:
            msg = "No file is active. First, run `activate [FILE]`"
            print(msg)
            return

        key, val = args[0], args[1]
        keys = key.split('.')

        # Checking for forbidden characters
        if len(re.findall(r"[^A-z\d.\[\]]", key)) > 0:
            msg = 'Forbidden characters found in given key. See `help set`'
            print(msg)
            return

        if MorlockCli.isjson(val):
            val = json.loads(val)

        isinvalid = lambda key: ('[' in key and not ']' in key) or ('[]' in key) or (']' in key and not '[' in key)
        islist = lambda key: '[' in key
        base = refr = copy.deepcopy(self.activefile.content['data'])
        last = keys[-1]

        for key in keys:
            # Key is of type key[a]...[z] (aka list)
            if islist(key):
                name, idxs = key.split('[', 1)
                idxs = idxs[:-1].split('][')
                exists = (name in refr)

                # Checking for keys with: only opening/ closing bracket; [] without index
                if isinvalid(key):
                    msg = 'Invalid key found. Aborting.'
                    print(msg)
                    return

                # Checking for keys without identifier (e.g.: [0][1][2])
                if name == '':
                    msg = "'{}' is an invalid key.".format(key)
                    print(msg)
                    return

                # refr[name] does not exist or isn't a list
                if not exists or not isinstance(refr[name], list):
                    refr[name] = []
                
                # Setting a reference 
                lst = refr[name]
                for i in range(len(idxs)):
                    idx = idxs[i]

                    # If list index is not a digit (e.g lst['a']; correct -> lst.a)
                    if not idx.isdigit():
                        msg = 'Forbidden non-digit index found. Aborting.'
                        print(msg)
                        return

                    islastidx = (i == len(idxs) - 1)
                    idx = int(idx)

                    # Handling indices out of bound of list
                    if not idx in range(-len(lst), len(lst) + 1):
                        msg = 'Given index is out of bounds. Aborting.'
                        print(msg)
                        return

                    # refr[name][idx-0][idx-1]...[idx-n] isn't a list
                    # Needs to recheck since it's in a loop
                    if not isinstance(lst, list):
                        lst = []

                    # If it's pushing time
                    if islastidx:
                        # Adding a new value
                        if idx == len(lst):
                            lst.append(val)
                        # Editing existing value
                        else:
                           lst[idx] = val

                    # Going deeper into the list
                    lst = lst[idx]
                
            # Key is of type key.a...z (aka dict)
            else:
                islastkey = (key == last)
                exists = (key in refr)

                # If that's the last iteration, set the value
                if islastkey:
                    refr[key] = val
                else:
                    # The user wants to set a deep-level dict
                    if not exists:
                        refr[key] = {}
                    elif not isinstance(refr[key], dict):
                        refr[key] = {}

                # Going deeper into the dict
                refr = refr[key]
            
        self.activefile.content['data'] = base

    def do_activate(self, path: str) -> None:
        morlockfile = self.findmorlockfile({'path': path})
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

    def do_deactivate(self, _: str=None) -> None:
        if self.activefile is None:
            msg = "There's no currently active file."
            print(msg)
            return

        self.activefile = None
        self.prompt = 'morlock> '

    def do_switch(self, path: str) -> None:
        '`switch [FILE]` is a shortcut for `deactivate; activate [FILE]`'

        morlockfile = self.findmorlockfile({'path': path})

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

    def findmorlockfiles(self, prop: dict) -> list[MorlockFile]:
        morlockfiles = []

        for loadedfile in self.loadedfiles:
            for key, val in prop.items():
                if hasattr(loadedfile, key) and getattr(loadedfile, key) == val:
                    morlockfiles.append(loadedfile)

        return morlockfiles

    def findmorlockfile(self, prop: dict) -> MorlockFile:
        morlockfiles = self.findmorlockfiles(prop)

        if len(morlockfiles) > 0:
            return morlockfiles[0]
        else:
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