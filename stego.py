#!/usr/bin/env python3
import cmd
import sys
import os
import signal
from termcolor import colored

file_types = ['jpeg', 'png', 'bmp', 'gif',
              'ttif-intel', 'ttif-motorola', 'xcf']
hex_headers = {
    'jpeg': [0xFF, 0xD8, 0xFF, 0xE0],
    'png': [0x89, 0x50, 0x4e, 0x47],
    'bmp': [0x42, 0x4d],
    'gif': [0x47, 0x49, 0x46, 0x38],
    'ttif-intel': [0x49, 0x49, 0x2a, 0x00],
    'ttif-motorola': [0x4d, 0x4d, 0x00, 0x2a],
    'xcf': [0x67, 0x69, 0x6d, 0x70, 0x20, 0x78, 0x63, 0x66, 0x20, 0x76]
}

hex_footers = {
    'jpeg': [0xFF, 0xD9],
    'png': None,
    'bmp': None,
    'gif': None,
    'ttif-intel': None,
    'ttif-motorola': None,
    'xcf': None
}


def r_bytes(in_file):
    """ Throws a FileNotFoundError if the file can't be opened.

        Returns an array of bytes for a given file.
    """
    return bytearray(open(in_file, 'rb').read())


def w_bytes(bytes, out_file):
    open(out_file, 'wb').write(bytes)


def is_valid(file, file_type=None):
    if file_type is None:
        for f_type in file_types:
            if is_valid(file, f_type):
                return [True, f_type]
        return [False, None]
    else:
        if file_type not in file_types:
            raise ValueError('Unknown file type: ' + file_type)

        b = r_bytes(file)
        header = hex_headers[file_type]

        for i in range(len(header)):
            if b[i] != header[i]:
                return False

        tail = hex_footers[file_type]

        if tail is not None:
            offset = len(b) - len(tail)
            for i in range(len(tail)):
                if b[i + offset] != tail[i]:
                    return [False, None]
        return [True, file_type]


def run_add(in_file, out_file, value):
    if value < 0:
        raise ValueError("Value must be positive.")
    elif value > 255:
        raise ValueError("Value must be less than or equal to 0xFF")

    b = r_bytes(in_file)
    for i in range(len(b)):
        b[i] = (b[i] + value) % 256
    w_bytes(b, out_file)


def run_subtract(in_file, out_file, value):
    if value < 0:
        raise ValueError("Value must be positive.")
    elif value > 255:
        raise ValueError("Value must be less than or equal to 0xFF")

    b = r_bytes(in_file)
    for i in range(len(b)):
        if b[i] <= value - 1:
            b[i] = 0xFF - value + 1 + b[i]
        else:
            b[i] -= value
    w_bytes(b, out_file)


def run_xor(in_file, out_file, value):
    b = r_bytes(in_file)
    for i in range(len(b)):
        b[i] ^= value
    w_bytes(b, out_file)


def auto_jpeg_xor(in_file, out_file):
    """Returns true if successful.
    """
    b = r_bytes(in_file)
    val = None
    if len(b) > 10:
        if b[4] != b[10]:
            print(colored('Running auto XOR on jpeg failed.', 'red'))
            return False
        val = b[4]

    print(colored('Running XOR with ' + hex(val) + '..', 'yellow'))
    run_xor(in_file, out_file, val)
    # if is_valid(out_file, 'jpeg'):
    if is_valid(out_file)[0]:
        print(colored('Image decoded.', 'green'))
    else:
        print(colored('Running auto XOR on jpeg failed.', 'red'))

    return True


def auto_jpeg_subtract(in_file, out_file):
    """Returns true if successful
    """
    b = r_bytes(in_file)
    val = None
    if len(b) > 10:
        if b[4] != b[10]:
            print(colored('Running auto SUBTRACT on jpeg failed.', 'red'))
            return False
        val = b[4]

    print(colored('Running SUBTRACT with ' + hex(val) + '..', 'yellow'))
    run_subtract(in_file, out_file, val)
    if jpeg_valid(out_file):
        print(colored('Image decoded.', 'green'))
    else:
        print(colored('Running auto SUBTRACT on jpeg failed.', 'red'))

    return True


def jpeg_valid(in_file):
    b = r_bytes(in_file)

    # Check the start sequence
    start_correct = (
        b[0] == 0xFF and
        b[1] == 0xD8 and
        b[2] == 0xFF and
        b[3] == 0xE0)

    # Check the ending sequence
    end_correct = (
        b[len(b) - 2] == 0xFF and
        b[len(b) - 1] == 0xD9)

    return (start_correct and end_correct)


def fix_path(path):
    return os.path.abspath(os.path.expanduser(path))


class CmdRunner(cmd.Cmd):
    # prompt = colored('(Stego) ', 'cyan')
    prompt = colored('>> ', 'cyan')
    intro = colored('''
   _____  _
  /  ___|| |
  \ `--. | |_  ___   __ _   ___   ___   __ _  _   _  _ __  _   _  ___
   `--. \| __|/ _ \ / _` | / _ \ / __| / _` || | | || '__|| | | |/ __|
  /\__/ /| |_|  __/| (_| || (_) |\__ \| (_| || |_| || |   | |_| |\__ \\
  \____/  \__|\___| \__, | \___/ |___/ \__,_| \__,_||_|    \__,_||___/
                     __/ |
                    |___/
    ''', 'green')

    cwd = None
    prev_cwd = None

    def __init__(self):
        self.cwd = os.getcwd()
        self.prev_cwd = os.getcwd()
        super(CmdRunner, self).__init__()

    def cmdloop(self, intro=None):
        """Repeatedly issue a prompt, accept input, parse an initial prefix
        off the received input, and dispatch to action methods, passing them
        the remainder of the line as argument.

        """
        try:
            self.preloop()
            if self.use_rawinput and self.completekey:
                try:
                    import readline
                    self.old_completer = readline.get_completer()
                    readline.set_completer(self.complete)
                    readline.set_completer_delims('/')
                    readline.parse_and_bind(
                        self.completekey + ": complete")
                except ImportError:
                    pass
            try:
                if intro is not None:
                    self.intro = intro
                if self.intro:
                    self.stdout.write(str(self.intro) + "\n")
                stop = None
                while not stop:
                    if self.cmdqueue:
                        line = self.cmdqueue.pop(0)
                    else:
                        if self.use_rawinput:
                            try:
                                line = input(self.prompt)
                            except EOFError:
                                line = 'EOF'
                        else:
                            self.stdout.write(self.prompt)
                            self.stdout.flush()
                            line = self.stdin.readline()
                            if not len(line):
                                line = 'EOF'
                            else:
                                line = line.rstrip('\r\n')
                    line = self.precmd(line)
                    stop = self.onecmd(line)
                    stop = self.postcmd(stop, line)
                self.postloop()
            finally:
                if self.use_rawinput and self.completekey:
                    try:
                        import readline
                        readline.set_completer(self.old_completer)
                    except ImportError:
                        pass
        except KeyboardInterrupt:
            self.intro = ''
            print()
            self.cmdloop()

    def do_jpeg_xor(self, line):
        args = line.split(' ')
        auto_jpeg_xor(fix_path(args[0]), fix_path(args[1]))

    def complete_jpeg_xor(self, text, line, begin_index, end_index):
        line_to_cursor = line[:end_index]

        start_line = line[:end_index].rsplit(' ', 1)[1]
        end_line = line[end_index:].split(' ', 1)[0]
        full_line = start_line + end_line

        if len(line_to_cursor.split(' ')) > 3:
            return

        abs_path = os.path.abspath(os.path.expanduser(start_line))

        if not os.path.exists(abs_path):
            arr = abs_path.rsplit('/', 1)
            abs_path = arr[0]
            name = arr[1]
            listing = os.listdir(abs_path)

            complete_listing = []
            for item in listing:
                if os.path.isdir(os.path.join(abs_path, item)):
                    complete_listing.append(item + '/')
                else:
                    complete_listing.append(item)
            return [item for item in complete_listing if item.startswith(name)]
        elif full_line.endswith('/'):
            listing = os.listdir(abs_path)
            return listing

    def do_validimg(self, line):
        path = fix_path(line)
        valid = is_valid(path)
        if valid[0]:
            print(colored('Valid ' + valid[1] + ' detected.', 'green'))
        else:
            print(colored('No valid image detected.', 'red'))

    def complete_validimg(self, text, line, begin_index, end_index):
        line_to_cursor = line[:end_index]

        start_line = line[:end_index].rsplit(' ', 1)[1]
        end_line = line[end_index:].split(' ', 1)[0]
        full_line = start_line + end_line

        if len(line_to_cursor.split(' ')) > 2:
            return

        abs_path = os.path.abspath(os.path.expanduser(start_line))

        if not os.path.exists(abs_path):
            arr = abs_path.rsplit('/', 1)
            abs_path = arr[0]
            name = arr[1]
            listing = os.listdir(abs_path)

            complete_listing = []
            for item in listing:
                if os.path.isdir(os.path.join(abs_path, item)):
                    complete_listing.append(item + '/')
                else:
                    complete_listing.append(item)
            return [item for item in complete_listing if item.startswith(name)]
        elif full_line.endswith('/') or full_line == '':
            listing = os.listdir(abs_path)
            return listing

    def do_xor(self, line):
        args = line.split(' ')
        xor_val = int(args[2], 16)
        run_xor(fix_path(args[0]), fix_path(args[1]), xor_val)

    def complete_xor(self, text, line, begin_index, end_index):
        line_to_cursor = line[:end_index]

        start_line = line[:end_index].rsplit(' ', 1)[1]
        end_line = line[end_index:].split(' ', 1)[0]
        full_line = start_line + end_line

        if len(line_to_cursor.split(' ')) > 3:
            if text == '':
                return ['0x']
            elif text.startswith('0x') and len(text) < 4:
                return

        abs_path = os.path.abspath(os.path.expanduser(start_line))

        if not os.path.exists(abs_path):
            arr = abs_path.rsplit('/', 1)
            abs_path = arr[0]
            name = arr[1]
            listing = os.listdir(abs_path)

            complete_listing = []
            for item in listing:
                if os.path.isdir(os.path.join(abs_path, item)):
                    complete_listing.append(item + '/')
                else:
                    complete_listing.append(item)
            return [item for item in complete_listing if item.startswith(name)]
        elif full_line.endswith('/'):
            listing = os.listdir(abs_path)
            return listing

    def do_subtract(self, line):
        args = line.split(' ')
        subtract_val = int(args[2], 16)
        run_subtract(args[0], args[1], subtract_val)

    def do_add(self, line):
        args = line.split(' ')
        add_val = int(args[2], 16)
        run_add(args[0], args[1], add_val)

    def do_pwd(self, line):
        print(os.getcwd())

    def do_cd(self, line):
        old_cwd = self.cwd
        old_prev_cwd = self.prev_cwd

        new_dir = line
        first_chr = line[:1]

        if line == '-':
            tmp = self.prev_cwd
            self.prev_cwd = self.cwd
            self.cwd = tmp
            new_dir = tmp
        elif line == '':
            self.cwd = '~'
            new_dir = '~'
        elif first_chr == '~' or first_chr == '/':
            new_dir = line
        else:
            new_dir = self.cwd + '/' + line

        try:
            os.chdir(os.path.expanduser(new_dir))
            self.prev_cwd = self.cwd
            self.cwd = os.getcwd()
        except FileNotFoundError:
            self.cwd = old_cwd
            self.prev_cwd = old_prev_cwd
            print(colored('No such file or directory: ' + line, 'red'))

    def complete_cd(self, text, line, begin_index, end_index):
        line_to_cursor = line[:end_index]

        start_line = line[:end_index].rsplit(' ', 1)[1]
        end_line = line[end_index:].split(' ', 1)[0]
        full_line = start_line + end_line

        if len(line_to_cursor.split(' ')) > 2:
            return

        abs_path = os.path.abspath(os.path.expanduser(start_line))

        if line_to_cursor == '':
            listing = os.listdir(abs_path)
            return listing

        if not os.path.exists(abs_path):
            arr = abs_path.rsplit('/', 1)
            abs_path = arr[0]
            name = arr[1]
            listing = os.listdir(abs_path)

            complete_listing = []
            for item in listing:
                if os.path.isdir(os.path.join(abs_path, item)):
                    complete_listing.append(item + '/')
                else:
                    complete_listing.append(item)
            return [item for item in complete_listing if item.startswith(name)]
        elif full_line.endswith('/'):
            listing = os.listdir(abs_path)
            return listing

    # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% #
    # Passed commands through to the shell if unrecognized. #
    # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% #

    def preloop(self):
        cmd.Cmd.preloop(self)  # sets up command completion
        self._hist = []  # No history yet
        self._locals = {}  # Initialize execution namespace for user
        self._globals = {}

    def default(self, line):
        os.system(line)

    # %%%%%%%%% #
    # END Shell #
    # %%%%%%%%% #

    def do_exit(self, line):
        print(colored('Stopping...\n', 'yellow'))
        return True

    def do_quit(self, line):
        print(colored('Stopping...\n', 'yellow'))
        return True

    def do_EOF(self, line):
        print(colored('\nStopping...\n', 'yellow'))
        return True


if __name__ == '__main__':
    CmdRunner().cmdloop()
