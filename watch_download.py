#!/usr/bin/env python
# -*- coding: utf-8 -*-

from time import sleep
from pathlib import Path
import subprocess as sp
import os

def launch_download(dir):
    url    = (dir/"url").read_text()
    format = (dir/"format").read_text()
    print(f"Start download of {url} in '{format}' format in {dir}")
    (dir/"commit").rename(dir/"inprogress")
    ret = sp.run(["echo", "yt-dlp", url] + ([ "--format", format] if format else []), cwd=dir)
    ret = sp.run(["yt-dlp", url] + ([ "--format", format] if format else []), cwd=dir)
    if ret.returncode == 0:
        (dir/"inprogress").rename(dir/"done")
    else:
        (dir/"inprogress").rename(dir/"retry")
    return
            

def main():
    # watch current dir for tmp dir creation with commit file
    while True:
        for dir in Path('.').glob("tmp*"):
            if not dir.is_dir(): continue
            if (dir / "commit").is_file() or\
                (dir/"retry").is_file():
                launch_download(dir)
        sleep(10)
    return 0

if __name__ == "__main__":
    main()
