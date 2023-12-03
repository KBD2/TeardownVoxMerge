import argparse

from voxutil import VoxFile

parser = argparse.ArgumentParser(
    prog='voxmerge.py'
)

parser.add_argument('filename', help='Main file')
parser.add_argument('files', nargs='*', help='List of files to merge into main')

args = parser.parse_args()

vox = VoxFile(args.filename)

for fileName in args.files:
    vox.merge(VoxFile(fileName))

vox.write("output.vox")