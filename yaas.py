import urllib.parse
from typing import Mapping, Sequence, Union

from jinja2 import StrictUndefined
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response, RedirectResponse
from starlette.templating import Jinja2Templates
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles
from starlette.background import BackgroundTask

import yt_dlp as youtube_dl
from time import sleep

__version__ = '1.0.0'

from pathlib import Path
__download_dir__ = Path("./downloads")

# https://stackoverflow.com/a/1094933
def human_filesize(num: Union[float, int], suffix: str = 'B') -> str:
    num = float(num)
    for unit in ('', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi'):
        if abs(num) < 1024.0:
            return f'{num:3.1f} {unit}{suffix}'
        num /= 1024.0
    return f'{num:.1f} Yi{suffix}'


def print_filesize(video: Mapping) -> str:
    filesize = video.get('filesize', video.get('filesize_approx'))
    return f'({human_filesize(filesize)})' if filesize else ''


def url_for_query(request: Request, name: str, **params: str) -> str:
    # https://github.com/encode/starlette/issues/560
    url = request.url_for(name)
    parsed = list(urllib.parse.urlparse(url))
    parsed[4] = urllib.parse.urlencode(params)
    return urllib.parse.urlunparse(parsed)


def handle_http_exception(request: Request, exc: HTTPException) -> Response:
    context = {
        'error': f'{exc.detail} (HTTP {exc.status_code})',
        'request': request
    }
    return templates.TemplateResponse('error.html', context)


ydl = youtube_dl.YoutubeDL({
    'no_color': True,
    'quiet': True,
    'skip_download': True
})
ydl.add_default_info_extractors()

templates = Jinja2Templates(directory='templates')
templates.env.undefined = StrictUndefined
templates.env.filters['print_filesize'] = print_filesize
templates.env.globals.update({
    'url_for_query': url_for_query,
    'youtubedl_version': youtube_dl.version.__version__,
    'yaas_version': __version__
})
exception_handlers = {
    HTTPException: handle_http_exception
}
routes = [
    Mount('/downloads', app=StaticFiles(directory=__download_dir__, html=True), name="downloads"),
]

# https://github.com/encode/starlette/issues/1142
app = Starlette(exception_handlers=exception_handlers, routes=routes)  # type: ignore


@app.route('/')
@app.route('/index.html')  # propriety
async def index(request: Request) -> Response:
    return templates.TemplateResponse('_base.html', {'request': request})


@app.route('/details')
async def fetch(request: Request) -> Response:
    try:
        url = request.query_params['url']
    except KeyError:
        return RedirectResponse(url=request.url_for('index'))
    else:
        if not url:
            return RedirectResponse(url=request.url_for('index'))

    try:
        videos = get_video_info(url)
    except youtube_dl.utils.DownloadError as e:
        # A handled youtube-dl error is still an HTTP 200 from us
        return templates.TemplateResponse('error.html', {'error': parse_err(e), 'request': request})
    except NotImplementedError as exc:
        return templates.TemplateResponse('error.html', {'error': str(exc), 'request': request})
    else:
        return templates.TemplateResponse('video.html', {'videos': videos, 'request': request, 'url': url})

@app.route('/details.json')
def fetch_json(request: Request) -> Response:
    url = request.query_params['url']
    return JSONResponse(get_video_info(url))

import tempfile
import os
@app.route('/download')
async def download(request: Request) -> Response:
    try:
        url = request.query_params['url']
    except KeyError:
        return RedirectResponse(url=request.url_for('index'))
    else:
        if not url:
            return RedirectResponse(url=request.url_for('index'))
    try:
        format = request.query_params['format']
    except KeyError:
        format = ""
    else:
        if not format:
            format = ""

    dir = tempfile.mkdtemp(dir=__download_dir__)
    dir_fd = os.open(dir, os.O_RDONLY)
    def opener(path, flags):
        return os.open(path, flags, dir_fd=dir_fd)
    with open('url', 'w', opener=opener) as f:
        print(url, file=f, end='')
    with open('format', 'w', opener=opener) as f:
        print(f"{format}", file=f, end='')
    with open('commit', 'w', opener=opener) as f:
        pass
    ans = f"Download {url} with format {format} in {dir}\n"
    return PlainTextResponse(ans)

    try:
        videos = get_video_info(url)
    except youtube_dl.utils.DownloadError as e:
        # A handled youtube-dl error is still an HTTP 200 from us
        return templates.TemplateResponse('error.html', {'error': parse_err(e), 'request': request})
    video = videos[0]

    title = video['title']
    if format is None:
        download_url = video['url']
    else:
        for cur_format in video['formats']:
            if cur_format['format_id'] == format:
                download_url = cur_format['url']
                filename = f"{title}.{cur_format['ext']}"
                break
    ans = f"Download {url} with format {format}: will download url:\n{download_url}\n"
    wgetBack = BackgroundTask(wget, url=download_url)
    return PlainTextResponse(ans, background=wgetBack)

import subprocess
async def wget(url):
    return

@app.route('/list_downloads')  # propriety
async def list_downloads(request: Request) -> Response:
    videos = []
    for d in __download_dir__.glob("tmp*"):
        if (d/"done").is_file():
            file = list(d.glob("*.*"))[0]
            url = (file.parent/"url").read_text()
            name = file.name
            file = file.relative_to(__download_dir__)
            dir = str(file.parent)
            v = (str(file), dir, name, url)
            videos.append(v)
    return templates.TemplateResponse('list_downloads.html', {'videos': videos, 'request': request})

@app.route('/remove_download')  # propriety
async def remove_download(request: Request) -> Response:
    try:
        dir = request.query_params['dir']
        if (__download_dir__/dir).is_dir():
            dir = __download_dir__/dir 
            for child in dir.iterdir():
                child.unlink(missing_ok=True)
            dir.rmdir()
    except KeyError:
        return RedirectResponse(url=request.url_for('index'))
    else:
        if not dir:
            return RedirectResponse(url=request.url_for('index'))
    return RedirectResponse(url=request.url_for('list_downloads'))

@app.route('/robots.txt')
def robots_txt(request: Request) -> Response:
    # Prevent indexing of any path except index
    robots_txt = (
        'User-Agent: *',
        'Allow: /index.html',
        'Allow: /$',  # nonstandard syntax
        'Disallow: /'
    )
    return PlainTextResponse('\n'.join(robots_txt))


# TODO: More playlist details
def get_video_info(url: str) -> Sequence[Mapping]:
    info = ydl.extract_info(url)
    # youtube_dl.extractors.common.InfoExtractor says we should assume _type
    # is 'video' if it is missing.
    media_type = info.get('_type', 'video')
    if media_type == 'video':
        return [info]
    elif media_type in ('playlist', 'multi_video'):
        return info['entries']
    else:
        raise NotImplementedError(f'Media type {info["_type"]} is supported by '
                                  'youtube-dl, but not by yaas.')


def parse_err(err: youtube_dl.utils.DownloadError) -> str:
    msg = err.args[0]
    log_prefix = 'ERROR: '
    invalid_url = [
        'is not a valid URL',
        'Name or service not known',
        'URLError'
    ]
    if any(err in msg for err in invalid_url):
        return 'The provided URL is invalid.'
    elif 'Unsupported URL' in msg:
        return 'The provided URL is not supported by youtube-dl.'
    elif msg.startswith(log_prefix):
        return f'Unknown error: {msg[len(log_prefix):]}'
    else:
        return f'Unknown error: {msg!r}'
