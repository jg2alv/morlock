import argparse
from Morlock import Morlock

def parse_args():
    parser = argparse.ArgumentParser(prog='morlock')
    parser.add_argument('file', nargs='?', default=None, type=str)
    parser.add_argument('-p', '--password', required=False, default=None, type=str)

    return parser.parse_args()

def main():
    args = parse_args()
    morlock = Morlock()

    morlock.set_file(args.file)
    morlock.set_password(args.password)
    morlock.cmdloop()

if __name__ == '__main__':
    main()