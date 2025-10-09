### Micro:bit file system exercsier v0.2

### MIT License

### Copyright (c) 2025 Kevin J. Walters

### Permission is hereby granted, free of charge, to any person obtaining a copy
### of this software and associated documentation files (the "Software"), to deal
### in the Software without restriction, including without limitation the rights
### to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
### copies of the Software, and to permit persons to whom the Software is
### furnished to do so, subject to the following conditions:

### The above copyright notice and this permission notice shall be included in all
### copies or substantial portions of the Software.

### THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
### IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
### FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
### AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
### LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
### OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
### SOFTWARE.


### This implements a work-in-progress file system check
### together with some file system operations designed to
### give the file system some exercise to provoke any lurking
### bugs


import machine
import os


### Hardware, page size nRF51 1k, nRF52 4k
page_size = 4096 if os.uname().machine.find("nRF52") >= 0 else 1024
lt_offset = page_size - 16

TBL_ID_FS = 0x03

def findlayouttable():
    ### Reverse scan through flash for magic numbers which indicate layout table
    ### TODO - forward might be better - make this configurable and default to forward
    mask32 = 0xffffffff
    for addr in range(0x80000 - page_size, 0 - page_size, 0 - page_size):
        ### The and (&) ensures mem32 are unsigned
        m1 = machine.mem32[addr + lt_offset + 0x00] & mask32
        m2 = machine.mem32[addr + lt_offset + 0x0c] & mask32
        tbl_ps = machine.mem16[addr + lt_offset + 0x0a]
        if m1 == 0x597f30fe and m2 == 0xc1b1d79d:
            if 1 << tbl_ps != page_size:
                raise Exception("Page size in layout table does not match hardware - OH NO!")
            return addr

    return None


def fsloc():
    sec_page_num = None
    sec_len = None
    table_page = findlayouttable()
    ### sloppy parsing hereby
    table_len = machine.mem16[table_page + lt_offset + 0x06]
    for offset in range(0 - table_len, 0, 16):
        row_addr = table_page + lt_offset + offset
        if machine.mem8[row_addr] == TBL_ID_FS:
            sec_page_num = machine.mem16[row_addr + 0x02]
            sec_len = machine.mem32[row_addr + 0x04]
            break

    return (sec_page_num * page_size, sec_page_num * page_size + sec_len) if sec_len is not None else (None, None)


### File system parameters
#fs_start=0x70000
#fs_end=0x78000
(fs_start, fs_end) = fsloc()
print("FS", hex(fs_start), hex(fs_end))
log_chunk_size=7


### Constants based on microbitfs.c
MAX_FILENAME_LENGTH = 120

FREED_CHUNK  = 0
PERSISTENT_DATA_MARKER = 253
FILE_START   = 254
UNUSED_CHUNK = 255

FILE_NOT_FOUND = 255    ### do i need this?



### Calculated values
chunk_size = 1 << log_chunk_size
chunk_count = (fs_end - fs_start) // chunk_size
data_per_chunk = chunk_size - 2
page_count = (fs_end - fs_start) // page_size
chunks_per_page = page_size // chunk_size
active_chunk_count = chunk_count - chunks_per_page

def fsck():
    unused = 0
    pdm = 0
    freed = 0
    chunk_fileuse = bytearray([0] * (active_chunk_count + 1))
    chunk_marker  = bytearray([0] * (active_chunk_count + 1))

    ### This moves around depending on the location of the page with the
    ### PERSISTENT_DATA_MARKER in it - that alternates between first and last
    ### page
    pdm_in_highpage = machine.mem8[fs_end - page_size] == PERSISTENT_DATA_MARKER
    pdm_in_lowpage = machine.mem8[fs_start] == PERSISTENT_DATA_MARKER
    base_chunk_addr = fs_start - chunk_size + (page_size if pdm_in_lowpage else 0)

    for index in range(1, active_chunk_count + 1):
        errors = {}
        chunk_ptr = base_chunk_addr + index * chunk_size
        marker = machine.mem8[chunk_ptr]
        chunk_marker[index] = marker
        if marker == FILE_START:
            end_offset = machine.mem8[chunk_ptr + 1]
            name_len = machine.mem8[chunk_ptr + 2]
            filename_b = bytes([machine.mem8[chunk_ptr + o_idx] for o_idx in range(3, min(name_len, MAX_FILENAME_LENGTH) + 3)])
            filename = filename_b.decode("utf-8")

            file_chunks = [index]
            file_chunks_backwards = [index]
            chunks_for_file = 1
            chunk_fileuse[index] += 1
            next_chunk_index = machine.mem8[chunk_ptr + chunk_size - 1]
            last_index = None
            while next_chunk_index != UNUSED_CHUNK:
                chunk_fileuse[next_chunk_index] += 1
                chunk_ptr = base_chunk_addr + next_chunk_index * chunk_size
                last_index = next_chunk_index
                prev_chunk_idx = machine.mem8[chunk_ptr]
                chunks_for_file += 1
                file_chunks.append(next_chunk_index)
                file_chunks_backwards.append(prev_chunk_idx)
                next_chunk_index = machine.mem8[chunk_ptr + chunk_size - 1]

            if last_index is not None:
                file_chunks_backwards.append(last_index)

            good_first_index = True
            if len(file_chunks_backwards) >= 2:
                ### The first entry should be duplicated, remove
                good_first_index = file_chunks_backwards[0] == file_chunks_backwards[1]
                if good_first_index:
                    _ = file_chunks_backwards.pop(0)

            good_fb = file_chunks == file_chunks_backwards

            print(filename, name_len, chunks_for_file, good_fb, good_first_index, file_chunks, file_chunks_backwards, end_offset)            
        elif marker == UNUSED_CHUNK:
            unused += 1
        elif marker == PERSISTENT_DATA_MARKER:
            pdm += 1
        elif marker == FREED_CHUNK:
            freed += 1

    used = sum([bool(chunk_fileuse[i]) for i in range(1, active_chunk_count + 1)])
    over_used = sum([1 if chunk_fileuse[i] > 1 else 0 for i in range(1, active_chunk_count + 1)])
    print("USED", used)
    print("UNUSED", unused)
    print("PDM IN ACTIVE", pdm)
    print("FREED", freed)
    print("OVER USED", over_used)
    print("PDM LOW (last)", pdm_in_lowpage, "PDM HIGH (first)", pdm_in_highpage)

    page_used = [False] * page_count
    for ac_index in range(1, chunk_count + 1):
        page_idx = (index - 1) // chunks_per_page   ### page numbering is unusual in C code, it's reversed
        if machine.mem8[fs_start - chunk_size + ac_index * chunk_size] not in (PERSISTENT_DATA_MARKER, UNUSED_CHUNK):
            page_used[page_idx] = True

    print("Pages in use", page_used)

    page_start = 1 if pdm_in_lowpage else 0
    print("Marker values")
    index = 1
    for page_idx in range(page_start, page_count - 1 + page_start):
        print(hex(fs_start + page_idx * page_size),
              [int(b) for b in chunk_marker[index:index + chunks_per_page]])
        index += chunks_per_page

    print("Chunks used by file count")
    index = 1
    for page_idx in range(page_start, page_count - 1 + page_start):
        print(hex(fs_start + page_idx * page_size),
              [int(b) for b in chunk_fileuse[index:index + chunks_per_page]])
        index += chunks_per_page

    return errors


e1 = fsck()

### TODO add some file system operations and repeat fsck after each one
