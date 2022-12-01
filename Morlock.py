import cmd, os, json, bcrypt, shlex, re, copy

OPEN_TAG = '<morlock>'
CLOSE_TAG = '</morlock>'
DEFAULT = { "name": None, "password": None, "data": {} }

class MorlockFile:
    path: str = None
    data: str = None
    wiped: bool = False
    content: dict = None
    modified: bool = False

    def __init__(self, path: str, data: str, content: dict) -> None:
        self.path = path
        self.data = data
        self.content = content

    def gen_bytes(self) -> bytes:
        if self.content == {}:
            data = ''
        else:
            content = json.dumps(self.content)
            data = OPEN_TAG + content + CLOSE_TAG

        return data.encode('utf-8')

class MorlockEmpty:
    pass

class MorlockCli(cmd.Cmd):
    intro = 'Welcome to morlock.\nType help or ? to list commands.\n'
    prompt = 'morlock> '

    loadedfiles: list[MorlockFile] = []
    activefile: MorlockFile = None

    def do_load(self, paths: str) -> None:
        'Load given file(s)'

        for path in shlex.split(paths):
            # If to-be-active file is already loaded
            if self.findmorlockfile({'path': path}) is not None:
                msg = "'{}' is already loaded. Maybe try `switch`?".format(path)
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
                
            open_tag = OPEN_TAG.encode('utf-8')
            close_tag = CLOSE_TAG.encode('utf-8')
            content = []

            # If there's no content in the file
            if not open_tag in byte or not close_tag in byte:
                msg = "Empty file detected. Loading defaults..."
                print(msg)
                default = copy.deepcopy(DEFAULT)
                msg = "Enter name: "
                name = input(msg)
                default['name'] = name
                msg = "Should the file be password-protected (y/n)? "
                isprotected = input(msg)
                
                isprotected = (isprotected.lower() == 'y')
                content = OPEN_TAG + json.dumps(default) + CLOSE_TAG
            else:
                # Reading until the start of MP3 content
                while not byte.startswith(b'ID3'):
                    content.append(byte[0])
                    byte = byte[1:]

                # Turning array of ints into string with the file's content
                content = ''.join(map(chr, content))
                isprotected = False
                
            # Saving the rest of the file
            data = byte

            # Getting `morlock` content inside of the file's head
            while not content.startswith(OPEN_TAG):
                content = content[1:]

            while not content.endswith(CLOSE_TAG):
                content = content[:-1]

            # Removing `morlock` tags
            content = content.replace(OPEN_TAG, '').replace(CLOSE_TAG, '')

            # Extracting JSON content
            while not MorlockCli.isjson(content) and content != '':
                content = content[1:]

            # If `morlock` content isn't JSON
            if not MorlockCli.isvalid(content):
                msg = "'{}' is possibly corrupted.".format(path)
                print(msg)
                continue

            content = json.loads(content)

            # If file is encrypted
            if content['password'] is not None:
                password = content['password']
                match = MorlockCli.passwordcheck(password, path)
                if not match:
                    msg = 'Incorrect password entered.'
                    print(msg)
                    continue
            else:
                password = None

            msg = "'{}' loaded successfully.".format(path)
            morlockfile = MorlockFile(path, data, content)
            self.loadedfiles.append(morlockfile)
            print(msg)

            if isprotected:
                self.do_lock(morlockfile.path)

    def do_unload(self, paths: str) -> None:
        'Unload given MorlockFile(s)'

        def unload(path: str) -> None:
            # Finding file with given path            
            morlockfile = self.findmorlockfile({'path': path})

            # If no file's found, maybe it wasn't loaded.
            if morlockfile is None:
                msg = "'{}' is not currently loaded.".format(path)
                print(msg)
                return

            # If the file to be unloaded was modified and not saved
            if morlockfile.modified:
                msg = "'{}' was modified. Do you wish to close it and discard changes (y/n)? ".format(path)
                discard = input(msg)

                while discard.lower() not in ['y', 'n']:
                    discard = input(msg)

                if discard == 'n':
                    return

            # Deactivating it if it was active    
            if self.activefile == morlockfile:
                self.do_deactivate()

            msg = "'{}' successfully unloaded.".format(path)
            self.loadedfiles.remove(morlockfile)
            print(msg)

        if paths != '':
            for path in shlex.split(paths):
                unload(path)
        elif self.activefile is not None:
            unload(self.activefile.path)
        else:
            msg = "There's no active file and zero files were given to be unloaded."
            print(msg)

    def do_reload(self, paths: str) -> None:
        'Shortcut to `unload [FILE]; load [FILE]'

        def reload(path: str) -> None:
            self.do_unload(path)
            self.do_load(path)

        if paths != '':
            for path in shlex.split(paths):
                reload(path)
        elif self.activefile is not None:
            reload(self.activefile.path)
        else:
            msg = 'There were no given files to be reloaded.'
            print(msg)

    def do_list(self, paths: str) -> None:
        "Print data that's saved on file(s) - given or active"

        def llist(path: str) -> None:
            # Finding file with given path
            morlockfile = self.findmorlockfile({'path': path})
            
            # If no file's found
            if morlockfile is None:
                msg = "'{}' is not currently loaded.".format(path)
                print(msg)
                return
            
            content = json.dumps(morlockfile.content, ensure_ascii=False, indent=4)
            print(content)


        if paths != '':
            for path in shlex.split(paths):
                llist(path)
        elif self.activefile is not None:
            llist(self.activefile.path)
        else:
            msg = "There's no active file and zero files were given to perform `list` on."
            print(msg)

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
                    self.activefile.modified = True
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
                            self.activefile.modified = True
                            lst.append(val)
                        # Editing existing value
                        elif MorlockCli.listgetdefault(lst, idx) != val:
                            self.activefile.modified = True
                            lst[idx] = val

                    # Going deeper into the list
                    lst = lst[idx]
                
            # Key is of type key.a...z (aka dict)
            else:
                islastkey = (key == last)
                exists = (key in refr)

                # If that's the last iteration, set the value
                if islastkey:
                    if refr.get(key, MorlockEmpty) != val:
                        self.activefile.modified = True
                        refr[key] = val
                else:
                    # The user wants to set a deep-level dict
                    if not exists:
                        self.activefile.modified = True
                        refr[key] = {}
                    elif not isinstance(refr[key], dict):
                        self.activefile.modified = True
                        refr[key] = {}

                # Going deeper into the dict
                refr = refr[key]
            
        self.activefile.content['data'] = base

    def do_activate(self, path: str) -> None:
        'Activate given MorlockFile'

        # Finding file with given path
        morlockfile = self.findmorlockfile({'path': path})
        if morlockfile is None:
            msg = "'{}' is not currently loaded.".format(path)
            print(msg)
            return

        if self.activefile is None:
            self.activefile = morlockfile
            self.prompt = 'morlock({})> '.format(path)
            msg = "'{}' activated successfully.".format(path)
            print(msg)
        else:
            path = self.activefile.path
            msg = "'{}' is currently active.".format(path)

    def do_deactivate(self, _: str=None) -> None:
        'Deactivate currently active MorlockFile'

        # If there's no active file
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
            msg = "'{}' is not loaded.".format(path)
            print(msg)
        else:
            if self.activefile is not None:
                self.do_deactivate()
            
            self.do_activate(path)

    def do_save(self, paths: str) -> None:
        'Save given MorlockFile(s) (e.g.: `save`, `save file1 file2 file3`)'

        def save(path: str) -> None:
            # Finding given file
            morlockfile = self.findmorlockfile({ 'path': path })
            if morlockfile is None:
                msg = "File '{}' not found.".format(path)
                print(msg)
                return
            elif not morlockfile.modified and not morlockfile.wiped:
                msg = "File '{}' was not modified; skipping.".format(path)
                print(msg)
                return

            with open(morlockfile.path, 'wb') as f:
                # Joining content to prepend file
                oldcontent = morlockfile.data
                newcontent = morlockfile.gen_bytes()
                f.write(newcontent + oldcontent)

                if morlockfile.wiped:
                    morlockfile.wiped = False
                    wasactive = False
                    msg = "'{}' saved successfully. Unloading file...".format(morlockfile.path)
                    print(msg)
                    self.do_unload(morlockfile.path)
                else:
                    morlockfile.modified = False
                    wasactive = (self.activefile == morlockfile)
                    msg = "'{}' saved successfully. Reloading file...".format(morlockfile.path)
                    print(msg)
                    self.do_reload(morlockfile.path)

                # Re-activating if necessary
                if wasactive:
                    self.do_activate(morlockfile.path)

        if paths != '':
            for path in shlex.split(paths):
                save(path)
        elif self.activefile is not None:
            save(self.activefile.path)
        else:
            msg = "There's no active file and zero files were given to be saved."
            print(msg)
            return

    def do_unlock(self, paths: str) -> None:
        'Remove password from given MorlockFile(s)'

        def unlock(path: str) -> None:
            # Finding given file
            morlockfile = self.findmorlockfile({ 'path': path })
            if morlockfile is None:
                msg = "'{}' not found.".format(path)
                print(msg)
                return

            # If it already has no password
            if morlockfile.content['password'] is None:
                msg = "'{}' has already no password.".format(path)
                print(msg)
                return

            # Checking if given password is the correct one
            match = MorlockCli.passwordcheck(morlockfile.content['password'], path)
            if match:
                morlockfile.modified = True
                morlockfile.content['password'] = None
                msg = "'{}' unlocked successfully.".format(path)
                print(msg)
            else:
                msg = "Wrong password inserted."
                print(msg)

        if paths != '':
            for path in shlex.split(paths):
                unlock(path)
        elif self.activefile is not None:
            unlock(self.activefile.path)
        else:
            msg = "There's no active file and zero files were given to be unlocked."
            print(msg)
            return

    def do_lock(self, paths: str) -> None:
        'Set password for given MorlockFile(s)'

        def lock(path: str) -> None:
            morlockfile = self.findmorlockfile({ 'path': path })

            # If no files were found
            if morlockfile is None:
                msg = "'{}' not found.".format(path)
                print(msg)
                return

            # Checking for existing password (user must provide in order to change it)
            if morlockfile.content['password'] is not None:
                msg = "'{}' is locked.".format(path)
                print(msg)
                match = MorlockCli.passwordcheck(morlockfile.content['password'], path)
                if not match:
                    msg = 'Wrong password inserted.'
                    print(msg)
                    return

            # Getting and setting new password
            msg = "Type in new password for '{}': ".format(path)
            newpassword = input(msg)
            newpassword = bcrypt.hashpw(newpassword.encode('utf-8'), bcrypt.gensalt())
            morlockfile.content['password'] = newpassword.decode('utf-8')
            morlockfile.modified = True
            msg = "Password for '{}' changed successfully.".format(path)
            print(msg)

        if paths != '':
            for path in shlex.split(paths):
                lock(path)
        elif self.activefile is not None:
            lock(self.activefile.path)
        else:
            msg = "There's no active file and zero files were given to be locked."
            print(msg)
            return

    def do_clear(self, paths: str, all: bool=False) -> None:
        "Clear morlock file's data"

        def clear(path: str) -> None:
            # Find given file
            morlockfile = self.findmorlockfile({'path': path})

            if morlockfile is None:
                msg = "'{}' is not loaded; skipping...".format(path)
                print(msg)
                return

            # Should wipe everything?
            if all:
                morlockfile.content = {}
                morlockfile.wiped = True
                msg = "'{}' wiped successfully.".format(path)
            else:
                # If file wasn't already wiped
                if 'data' in morlockfile.content:
                    morlockfile.modified = True
                    morlockfile.content['data'] = {}
                    msg = "'{}' cleared successfully.".format(path)
                else:
                    msg = "'{}' was already wiped before.".format(path)

            print(msg)

        if paths != '':
            for path in shlex.split(paths):
                clear(path)
        elif self.activefile is not None:
            clear(self.activefile.path)
        else:
            msg = ''
            print(msg)

    def do_wipe(self, paths: str) -> None:
        'Remove all traces of Morlock from file'
        self.do_clear(paths, all=True)
 
    def do_EOF(self, _) -> bool:
        'Clean up and exit'

        modifiedfiles = self.findmorlockfiles({ 'modified': True })
        if len(modifiedfiles) > 0:
            msg = "\nThere are modified files. Do you want to quit and discard all changes (y/n)? "
            action = input(msg)

            if action.lower() == 'n':
                return False

        print(sep='')
        return True

    def do_quit(self, _) -> bool:
        'Alias to EOF'
        return self.do_EOF(_)

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

    @staticmethod
    def passwordcheck(psw: str, path: str) -> bool:
        msg = "Type in password for '{}': ".format(path)
        password = input(msg)
        return bcrypt.checkpw(password.encode('utf-8'), psw.encode('utf-8'))

    @staticmethod
    def listgetdefault(lst: list, idx: int, default=MorlockEmpty):
        try:
            return lst.index(idx)
        except ValueError:
            return default