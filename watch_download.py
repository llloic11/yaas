#!/usr/bin/env python
# -*- coding: utf-8 -*-

from time import sleep
from pathlib import Path
import subprocess as sp
import os

def launch_download(dir):
    url    = (dir/"url").read_text()
    format = (dir/"format").read_text()
    try:
        (dir/"commit").rename(dir/"inprogress")
    except FileNotFoundError:
        try:
            (dir/"retry").rename(dir/"inprogress")
        except FileNotFoundError:
            return
    current_retry = (dir/"inprogress").read_text()
    current_retry = 0 if current_retry == "" else int(current_retry)
    print(f"Start download of {url} in '{format}' format in {dir}: try #{current_retry}")
    ret = sp.run(["echo", "yt-dlp", url] + ([ "--format", format] if format else []), cwd=dir)
    ret = sp.run(["yt-dlp", url] + ([ "--format", format] if format else []), cwd=dir)
    if ret.returncode == 0:
        (dir/"inprogress").rename(dir/"done")
    elif current_retry >= 10:
        (dir/"inprogress").rename(dir/"failed")
    else:
        (dir/"inprogress").rename(dir/"retry")
        (dir/"retry").write_text(str(current_retry+1))
    return


def main():
    # watch current dir for tmp dir creation with commit file
    while True:
        for dir in Path('.').glob("tmp*"):
            if not dir.is_dir(): continue
            if (dir / "commit").is_file() or\
                (dir/"retry").is_file():
                try:
                    launch_download(dir)
                except Exception as e:
                    print(e)
                    try:
                        (dir/"inprogress").rename(dir/"retry")
                    except:
                        pass
        sleep(10)
    return 0

if __name__ == "__main__":
    main()
