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


def run_auto_xor(in_file, out_file):
    """Returns true if successful.
    """
    b = r_bytes(in_file)

    valid = None
    for i in range(256):
        if i % 16 == 0:
            print(colored((str(100 * i / 256) + '% done'), 'yellow'))
        run_xor(in_file, out_file, i)
        valid = is_valid(out_file)
        if valid[0]:
            print(colored('Found image by XOR with ' + hex(i) + '.', 'green'))
            break

    if valid[0]:
        print(colored('Decoded ' + valid[1] + '.', 'green'))
    else:
        print(colored('Running XOR failed.', 'red'))
    return valid[0]


def run_auto_shift(in_file, out_file):
    """Returns true if successful.
    """
    b = r_bytes(in_file)

    valid = None
    for i in range(256):
        if i % 16 == 0:
            print(colored((str(100 * i / 256) + '% done'), 'yellow'))
        run_subtract(in_file, out_file, i)
        valid = is_valid(out_file)
        if valid[0]:
            print(colored('Found image by SUBTRACTING with ' + hex(i) + '.',
                          'green'))
            break

    if valid[0]:
        print(colored('Decoded ' + valid[1] + '.', 'green'))
    else:
        print(colored('Running SUBTRACTING failed.', 'red'))
    return valid[0]


def run_lsb_bitmap(in_file, out_file, num_bits=1):
    b = r_bytes(in_file)

    out_bits = []
    for byte in b:
        out_bits.append(byte & (0xFF >> 8 - num_bits))

    out_bytes = []

    # Pad with 0 bits if needed
    padded_bits = 0
    while len(out_bytes) % 8 != 0:
        padded_bits += 1
        out_bytes.append(0)

    if padded_bits != 0:
        print(colored('Padded file with ' + padded_bits + ' zero bits.',
                      'yellow'))

    for bit_start in range(0, len(out_bits), 8):
        byte = 0
        for i in range(8):
            byte += out_bits[bit_start + i] << 7 - i
        out_bytes.append(byte)

    w_bytes(bytearray(out_bytes), out_file)


def fix_path(path):
    return os.path.abspath(os.path.expanduser(path))


class CmdRunner(cmd.Cmd):
    # prompt = colored('(Stego) ', 'cyan')
    prompt = colored('>> ', 'cyan')
    intro = colored('''
          _                _               _
__      _| |__   ___  __ _| |_   ___ _   _| |__
\ \ /\ / / '_ \ / _ \/ _` | __| / __| | | | '_ \\
 \ V  V /| | | |  __/ (_| | |_  \__ \ |_| | |_) |
  \_/\_/ |_| |_|\___|\__,_|\__| |___/\__,_|_.__/
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

    def do_auto_xor(self, line):
        args = line.split(' ')
        run_auto_xor(fix_path(args[0]), fix_path(args[1]))

    def complete_auto_xor(self, text, line, begin_index, end_index):
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
        elif full_line.endswith('/') or full_line == '':
            listing = os.listdir(abs_path)
            return listing

    def do_auto_shift(self, line):
        args = line.split(' ')
        run_auto_shift(fix_path(args[0]), fix_path(args[1]))

    def complete_auto_shift(self, text, line, begin_index, end_index):
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
        elif full_line.endswith('/') or full_line == '':
            listing = os.listdir(abs_path)
            return listing

    def do_lsb(self, line):
        args = line.split(' ')
        run_lsb_bitmap(fix_path(args[0]), fix_path(args[1]),
                       num_bits=int(args[2]))

    def complete_lsb(self, text, line, begin_index, end_index):
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
        elif full_line.endswith('/') or full_line == '':
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
