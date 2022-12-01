# morlock

Morlock is a Python CLI to write JSON data into audio files inspired by the show Mr Robot.

### Usage

The tool is a command line interface. Therefore, one must enter commands to be executed. Multiple files can be loaded and one can be activated (which makes it the default file throught the software). For every action, one may type in `action file1 file2 file3... fileN` or simply `action`. In the first case, the script will loop through each of the given files, performing the commanded action. In the latter, the script will perform `action` in the active file (and display a warning in case there's none).

### Commands

* `load`: loads the given file(s). A file must be loaded before having actions performed on it. This action demands at least one argument.
* `unload`: unloads the given file(s). Will unload the active file if no arguments are given. Will display a warning if the file to be unloaded has unsaved changes.
* `reload`: shortcut to `unload [GIVEN]; load [GIVEN]`.
* `set`: allows the user to set a property in the file's JSON heading. Properties may be concatenated (e.g `family.brothers[0].son.favorite_game`). One may access a key using: 
    * `key` in case it's a `string`, an `integer` or a `boolean`
    * `key.prop` in case it's a dictionary
    * `key[0]` in case it's an array
* `activate`: activates given file. Takes only a single file.
* `deactivate`: deactivates given file. Takes no files.
* `switch`: shortcut to `deactivate [ACTIVE]; activate [GIVEN]`. Takes only a single file.
* `save`: writes changes into hardidsk-file. No change will take effect if one quits the CLI without running a save command.
* `unlock`: removes the password from a password-protected file. The user must provide the currently-used password of the file in order to remove it.
* `lock`: sets a new password for a file. The user must provide the currently-used password of the file (if any) in order to change it.
* `EOF`: quits the program. Will prompt the user if there are unsaved changes.