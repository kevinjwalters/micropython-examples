#!/usr/bin/python3

# SPDX-FileCopyrightText: 2025 Kevin J. Walters
#
# SPDX-License-Identifier: MIT

# Read indexed PNG files and output the pixel data and palette
# as Python variables to stdout
 
# Intended for use with GurgleApps Word Clock software
# see https://www.instructables.com/member/kevinjwalters/


import getopt
import sys
import array
import struct

### PyPNG library
import png


### globals
debug = 0
verbose = False
output = None


def usage(exit_code):
    print("pngtocode: [-h] [-o outputfilename] [-v]",
          file=sys.stderr)
    if exit_code is not None:
        sys.exit(exit_code)

def main(cmdlineargs):
    global debug, fps, movie_file, output
    global threshold, verbose

    try:
        opts, args = getopt.getopt(cmdlineargs,
                                   "ho:v", ["help", "output="])
    except getopt.GetoptError as err:
        print(err,
              file=sys.stderr)
        usage(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage(0)
        elif opt in ("-o", "--output"):
            output = arg
        elif opt == "-v":
            verbose = True
        else:
            print("BAD OPTION",
                  file=sys.stderr)
            sys.exit(2)

    filelist = args

    if output is not None and len(filelist) > 1:
        print("Must not specifiy output file with multiple files",
              file=sys.stderr)
        sys.exit(2)

    for f_idx, filename in enumerate(filelist):
       width, height, pixel_gen, metadata = png.Reader(filename).read()

       if output is not None:
           raise NotImplementedError("TODO - file output")

       palette = metadata.get("palette")
       if palette is None:
            print(f"{filename} is not an indexed PNG.",
                  file=sys.stderr)
            continue

       basevarname = f"VAR{f_idx + 1}"
       assign = f"{basevarname} = bytearray(["
       print(assign, end="")
       indent = " " * len(assign)
       # This would use a lot of memory if PNGs happened to be large
       pixel_list = list(pixel_gen)
       last_idx = len(pixel_list) - 1
       for r_idx, row in enumerate(pixel_list):
           vals = [idx for idx in row]
           max_val = max(vals)
           fixed_len = len(str(max_val))
           print(("" if r_idx == 0 else indent),
                 ", ".join([str(val).zfill(fixed_len) for val in vals]),
                 sep="",
                 end="\n" if r_idx == last_idx else ",\n")
       print(indent[:len(indent) -1], "])", sep="")

       assign = f"{basevarname}_PALETTE = ["
       print(assign, end="")
       indent = " " * len(assign)
       last_idx = len(palette) - 1
       for p_idx, colour in enumerate(palette):
           if len(colour) >= 4 and colour[3] == 0:
               var_text = "MatrixBackground.TRANSPARENT"
           else:
               var_text = str(tuple(colour[:3]))
           print(("" if p_idx == 0 else indent),
                 var_text,
                 sep="",
                 end="\n" if p_idx == last_idx else ",\n")
       print(indent[:len(indent) -1], "]", sep="")


if __name__ == "__main__":
    main(sys.argv[1:])
