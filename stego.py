#!/usr/bin/env python3
import cmd
import sys
import os
import signal
from termcolor import colored


# def complete_allfiles(self, text, line, begin_index, end_index):
#     start_line = line[:end_index].rsplit(' ', 1)[1]
#     end_line = line[end_index:].split(' ', 1)[0]
#     full_line = start_line + end_line
#     abs_path = os.path.abspath(os.path.expanduser(start_line))

#     if not os.path.exists(abs_path):
#         arr = abs_path.rsplit('/', 1)
#         abs_path = arr[0]
#         name = arr[1]
#         listing = os.listdir(abs_path)

#         complete_listing = []
#         for item in listing:
#             if os.path.isdir(os.path.join(abs_path, item)):
#                 complete_listing.append(item + '/')
#             else:
#                 complete_listing.append(item)
#         # dirs = [d for d in listing if os.path.isdir(
#         #     os.path.join(abs_path, d))]
#         # complete_dirs = [d + '/' for d in listing]
#         return [item for item in complete_listing if item.startswith(name)]
#     elif full_line.endswith('/'):
#         listing = os.listdir(abs_path)
#         # dirs = [item for item in listing if os.path.isdir(
#         #     os.path.join(abs_path, item))]
#         return listing

# def complete_onlydirs(self, text, line, begin_index, end_index):
#     start_line = line[:end_index].rsplit(' ', 1)[1]
#     end_line = line[end_index:].split(' ', 1)[0]
#     full_line = start_line + end_line
#     abs_path = os.path.abspath(os.path.expanduser(start_line))

#     if not os.path.exists(abs_path):
#         arr = abs_path.rsplit('/', 1)
#         abs_path = arr[0]
#         name = arr[1]
#         listing = os.listdir(abs_path)

#         dirs = [d for d in listing if os.path.isdir(
#             os.path.join(abs_path, d))]
#         complete_dirs = [d + '/' for d in listing]
#         return [item for item in complete_dirs if item.startswith(name)]
#     elif full_line.endswith('/'):
#         listing = os.listdir(abs_path)
#         dirs = [item for item in listing if os.path.isdir(
#             os.path.join(abs_path, item))]
#         return dirs

def run_add(in_file, out_file, value):
    if value < 0:
        raise ValueError("Value must be positive.")
    elif value > 255:
        raise ValueError("Value must be less than or equal to 0xFF")

    b = bytearray(open(in_file, 'rb').read())
    for i in range(len(b)):
        b[i] = (b[i] + value) % 256
    open(out_file, 'wb').write(b)


def run_subtract(in_file, out_file, value):
    if value < 0:
        raise ValueError("Value must be positive.")
    elif value > 255:
        raise ValueError("Value must be less than or equal to 0xFF")

    b = bytearray(open(in_file, 'rb').read())
    for i in range(len(b)):
        if b[i] <= value - 1:
            b[i] = 0xFF - value + 1 + b[i]
        else:
            b[i] -= value
    open(out_file, 'wb').write(b)


def run_xor(in_file, out_file, value):
    b = bytearray(open(in_file, 'rb').read())
    for i in range(len(b)):
        b[i] ^= value
    open(out_file, 'wb').write(b)


def auto_jpeg_xor(in_file, out_file):
    """Returns true if successful
    """
    b = bytearray(open(in_file, 'rb').read())
    val = None
    if len(b) > 10:
        if b[4] != b[10]:
            print(colored('Running auto XOR on jpeg failed.', 'red'))
            return False
        val = b[4]

    print(colored('Running XOR with ' + hex(val) + '..', 'yellow'))
    run_xor(in_file, out_file, val)
    if jpeg_valid(out_file):
        print(colored('Image decoded.', 'green'))
    else:
        print(colored('Running auto XOR on jpeg failed.', 'red'))

    return True


def auto_jpeg_subtract(in_file, out_file):
    """Returns true if successful
    """
    b = bytearray(open(in_file, 'rb').read())
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
    b = bytearray(open(in_file, 'rb').read())

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
    prompt = colored('(Stego) ', 'cyan')
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

    def cmdloop(self):
        try:
            cmd.Cmd.cmdloop(self)
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

    def do_xor(self, line):
        args = line.split(' ')
        xor_val = int(args[2], 16)
        run_xor(fix_path(args[0]), fix_path(args[1]), xor_val)

    def complete_xor(self, text, line, begin_index, end_index):
        print('\n' + text + '\n')
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

    def preloop(self):
        cmd.Cmd.preloop(self)  # sets up command completion
        self._hist = []  # No history yet
        self._locals = {}  # Initialize execution namespace for user
        self._globals = {}

    def default(self, line):
        os.system(line)

    # def do_clear(self, line):
    #     os.system('clear')

    # def do_pwd(self, line):
    #     print(os.getcwd())

    # def do_ls(self, line):
    #     os.system('ls')

    # def do_cd(self, line):
    #     old_cwd = self.cwd
    #     old_prev_cwd = self.prev_cwd

    #     new_dir = line
    #     first_chr = line[:1]

    #     if line == '-':
    #         tmp = self.prev_cwd
    #         self.prev_cwd = self.cwd
    #         self.cwd = tmp
    #         new_dir = tmp
    #     elif line == '':
    #         self.cwd = '~'
    #         new_dir = '~'
    #     elif first_chr == '~' or first_chr == '/':
    #         self.cwd = line
    #     else:
    #         self.cwd += '/' + line

    #     try:
    #         os.chdir(os.path.expanduser(new_dir))
    #     except FileNotFoundError:
    #         self.cwd = old_cwd
    #         self.prev_cwd = old_prev_cwd
    #         print(colored('No such file or directory: ' + line, 'red'))

    # def complete_cd(self, text, line, begin_index, end_index):
    #     true_text = line.split(' ', 1)[1]
    #     abs_path = os.path.abspath(os.path.expanduser(true_text))

    #     if not os.path.exists(abs_path):
    #         arr = abs_path.rsplit('/', 1)
    #         abs_path = arr[0]
    #         name = arr[1]
    #         listing = os.listdir(abs_path)
    #         dirs = [d for d in listing if os.path.isdir(
    #             os.path.join(abs_path, d))]
    #         return [item for item in dirs if item.startswith(name)]
    #     elif line.endswith('/'):
    #         listing = os.listdir(abs_path)
    #         dirs = [item for item in listing if os.path.isdir(
    #             os.path.join(abs_path, item))]
    #         return dirs

    def do_exit(self, line):
        print(colored('Stopping...\n', 'yellow'))
        return True

    def do_EOF(self, line):
        print(colored('\nStopping...\n', 'yellow'))
        return True


if __name__ == '__main__':
    CmdRunner().cmdloop()
