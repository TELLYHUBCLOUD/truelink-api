from fastapi import APIRouter, Query, HTTPException
from urllib.parse import quote_plus, urlparse, unquote, quote
import aiohttp
import logging
import re
import json
import requests
from cloudscraper import create_scraper
from requests import Session
from bs4 import BeautifulSoup
from lxml import etree
from base64 import standard_b64encode
from uuid import uuid4
import asyncio
import time
import math
import os
from math import floor, pow
from time import sleep

router = APIRouter()
logger = logging.getLogger(__name__)

# ======================== CONFIGURATION ======================== #
try:
    with open("config.json") as f:
        CONFIG = json.load(f)
except:
    CONFIG = {}

def get_config(key, default=None):
    return os.environ.get(key) or CONFIG.get(key, default)

# Service tokens
UPTOBOX_TOKEN = get_config("UPTOBOX_TOKEN")
TERA_COOKIE = get_config("TERA_COOKIE")
API_TOKEN = get_config("API_TOKEN")

if TERA_COOKIE:
    TERA_COOKIE = {"ndus": TERA_COOKIE}
else:
    TERA_COOKIE = None

# Supported services lists
ddllist = [
    "1drv.ms", "1fichier.com", "4funbox", "akmfiles", "anonfiles.com",
    "antfiles.com", "bayfiles.com", "disk.yandex.com", "fcdn.stream",
    "femax20.com", "fembed.com", "fembed.net", "feurl.com", "filechan.org",
    "filepress", "github.com", "hotfile.io", "hxfile.co", "krakenfiles.com",
    "layarkacaxxi.icu", "letsupload.cc", "letsupload.io", "linkbox",
    "lolabits.se", "mdisk.me", "mediafire.com", "megaupload.nz", "mirrobox",
    "mm9842.com", "momerybox", "myfile.is", "naniplay.com", "naniplay.nanime.biz",
    "naniplay.nanime.in", "nephobox", "openload.cc", "osdn.net", "pixeldrain.com",
    "racaty", "rapidshare.nu", "sbembed.com", "sbplay.org", "share-online.is",
    "shrdsk", "solidfiles.com", "streamsb.net", "streamtape", "terabox",
    "teraboxapp", "upload.ee", "uptobox.com", "upvid.cc", "vshare.is",
    "watchsb.com", "we.tl", "wetransfer.com", "yadi.sk", "zippyshare.com"
]

fmed_list = [
    "fembed.net", "fembed.com", "femax20.com", "fcdn.stream", "feurl.com",
    "layarkacaxxi.icu", "naniplay.nanime.in", "naniplay.nanime.biz",
    "naniplay.com", "mm9842.com"
]

anonfilesBaseSites = [
    "anonfiles.com", "hotfile.io", "bayfiles.com", "megaupload.nz",
    "letsupload.cc", "filechan.org", "myfile.is", "vshare.is", "rapidshare.nu",
    "lolabits.se", "openload.cc", "share-online.is", "upvid.cc"
]

# ======================== HELPER FUNCTIONS ======================== #
def get_readable_time(seconds):
    periods = [('d', 86400), ('h', 3600), ('m', 60), ('s', 1)]
    result = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result.append(f"{int(period_value)}{period_name}")
    return ''.join(result) or "0s"

def is_share_link(url):
    return bool(re.match(
        r"https?:\/\/.+\.gdtot\.\S+|https?:\/\/(filepress|filebee|appdrive|gdflix|driveseed)\.\S+",
        url
    ))

# ======================== BYPASS FUNCTIONS ======================== #
def yandex_disk(url: str) -> str:
    api = "https://cloud-api.yandex.net/v1/disk/public/resources/download?public_key={}"
    cget = create_scraper().request
    try:
        return cget("get", api.format(url)).json()["href"]
    except:
        return "ERROR: File not found/Download limit reached"

def uptobox(url: str) -> str:
    try:
        file_id = re.findall(r"\bhttps?://.*uptobox\.com/(\w+)", url)[0]
        if UPTOBOX_TOKEN:
            file_link = f"https://uptobox.com/api/link?token={UPTOBOX_TOKEN}&file_code={file_id}"
        else:
            file_link = f"https://uptobox.com/api/link?file_code={file_id}"
        
        cget = create_scraper().request
        res = cget("get", file_link).json()
        
        if res["statusCode"] == 0:
            return res["data"]["dlLink"]
        elif res["statusCode"] == 16:
            sleep(1)
            waiting_token = res["data"]["waitingToken"]
            wait_time = res["data"]["waiting"]
            sleep(wait_time)
            res = cget("get", f"{file_link}&waitingToken={waiting_token}").json()
            return res["data"]["dlLink"]
        elif res["statusCode"] == 39:
            wait_time = get_readable_time(res['data']['waiting'])
            return f"ERROR: Uptobox is being limited please wait {wait_time}"
        else:
            return f"ERROR: {res['message']}"
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

def mediafire(url: str) -> str:
    final_link = re.findall(r"https?:\/\/download\d+\.mediafire\.com\/\S+\/\S+\/\S+", url)
    if final_link:
        return final_link[0]
    
    cget = create_scraper().request
    try:
        url = cget("get", url).url
        page = cget("get", url).text
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"
    
    final_link = re.findall(r"\'https?:\/\/download\d+\.mediafire\.com\/\S+\/\S+\/\S+\'", page)
    if not final_link:
        return "ERROR: No links found in this page"
    return final_link[0].strip("'")

def osdn(url: str) -> str:
    osdn_link = "https://osdn.net"
    cget = create_scraper().request
    try:
        page = BeautifulSoup(cget("get", url, allow_redirects=True).content, "lxml")
        info = page.find("a", {"class": "mirror_link"})
        link = unquote(osdn_link + info["href"])
        mirrors = page.find("form", {"id": "mirror-select-form"}).findAll("tr")
        urls = [re.sub(r"m=(.*)&f", f"m={data.find('input')['value']}&f", link) for data in mirrors[1:]]
        return urls[0]
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

def github(url: str) -> str:
    cget = create_scraper().request
    try:
        download = cget("get", url, stream=True, allow_redirects=False)
        return download.headers["location"]
    except:
        return "ERROR: Can't extract the link"

def hxfile(url: str) -> str:
    sess = Session()
    try:
        headers = {
            "content-type": "application/x-www-form-urlencoded",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.152 Safari/537.36",
        }

        data = {
            "op": "download2",
            "id": urlparse(url).path.strip("/"),
            "rand": "",
            "referer": "",
            "method_free": "",
            "method_premium": "",
        }

        response = sess.post(url, headers=headers, data=data)
        soup = BeautifulSoup(response.text, "html.parser")

        if btn := soup.find("a", class_="btn btn-dow"):
            return btn["href"]
        if unique := soup.find("a", id="uniqueExpirylink"):
            return unique["href"]
        return "ERROR: No download link found"
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

def letsupload(url: str) -> str:
    cget = create_scraper().request
    try:
        res = cget("POST", url)
        direct_link = re.findall(r"(https?://letsupload\.io\/.+?)\'", res.text)
        return direct_link[0] if direct_link else "ERROR: Direct Link not found"
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

def anonfilesBased(url: str) -> str:
    cget = create_scraper().request
    try:
        soup = BeautifulSoup(cget("get", url).content, "lxml")
        sa = soup.find(id="download-url")
        return sa["href"] if sa else "ERROR: File not found!"
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

def fembed(link: str) -> str:
    sess = Session()
    try:
        link = link.replace("/v/", "/f/")
        raw = sess.get(link)
        api = re.search(r"(/api/source/[^\"']+)", raw.text)
        if not api:
            return "ERROR: No source API found"
            
        raw = sess.post("https://layarkacaxxi.icu" + api.group(1)).json()
        result = {}
        for d in raw["data"]:
            f = d["file"]
            head = sess.head(f)
            direct = head.headers.get("Location", link)
            result[f"{d['label']}/{d['type']}"] = direct
        
        return list(result.values())[-1]
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

def sbembed(link: str) -> str:
    sess = Session()
    try:
        raw = sess.get(link).text
        soup = BeautifulSoup(raw, "html.parser")
        result = {}
        for a in soup.findAll("a", onclick=re.compile(r"^download_video[^>]+")):
            data = dict(zip(
                ["id", "mode", "hash"],
                re.findall(r"[\"']([^\"']+)[\"']", a["onclick"])
            ))
            data["op"] = "download_orig"
            raw = sess.get("https://sbembed.com/dl", params=data)
            soup = BeautifulSoup(raw.text, "html.parser")
            if direct := soup.find("a", text=re.compile("(?i)^direct")):
                result[a.text] = direct["href"]
        return list(result.values())[-1] if result else "ERROR: Direct link not found"
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

def onedrive(link: str) -> str:
    link_without_query = urlparse(link)._replace(query=None).geturl()
    direct_link_encoded = str(standard_b64encode(bytes(link_without_query, "utf-8")), "utf-8")
    direct_link1 = f"https://api.onedrive.com/v1.0/shares/u!{direct_link_encoded}/root/content"
    cget = create_scraper().request
    try:
        resp = cget("head", direct_link1)
        return resp.next.url if resp.status_code == 302 else "ERROR: Unauthorized link"
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

def pixeldrain(url: str) -> str:
    url = url.strip("/ ")
    file_id = url.split("/")[-1]
    if url.split("/")[-2] == "l":
        dl_link = f"https://pixeldrain.com/api/list/{file_id}/zip?download"
    else:
        dl_link = f"https://pixeldrain.com/api/file/{file_id}?download"
    
    cget = create_scraper().request
    try:
        resp = cget("get", f"https://pixeldrain.com/api/file/{file_id}/info").json()
        return dl_link if resp.get("success") else f"ERROR: {resp.get('message', 'Failed')}"
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

def antfiles(url: str) -> str:
    sess = Session()
    try:
        raw = sess.get(url).text
        soup = BeautifulSoup(raw, "html.parser")
        if a := soup.find(class_="main-btn", href=True):
            return "{0.scheme}://{0.netloc}/{1}".format(urlparse(url), a["href"])
        return "ERROR: Link not found"
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

def streamtape(url: str) -> str:
    response = requests.get(url)
    if videolink := re.findall(r"document.*((?=id\=)[^\"']+)", response.text):
        return "https://streamtape.com/get_video?" + videolink[-1]
    return "ERROR: Direct link not found"

def racaty(url: str) -> str:
    cget = create_scraper().request
    try:
        url = cget("GET", url).url
        res = cget("POST", url, data={"op": "download2", "id": url.split("/")[-1]})
        html_tree = etree.HTML(res.text)
        direct_link = html_tree.xpath("//a[contains(@id,'uniqueExpirylink')]/@href")
        return direct_link[0] if direct_link else "ERROR: Direct link not found"
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

def fichier(link: str) -> str:
    if not re.match(r"^([http:\/\/|https:\/\/]+)?.*1fichier\.com\/\?.+", link):
        return "ERROR: Wrong link format!"
    
    if "::" in link:
        pswd = link.split("::")[-1]
        url = link.split("::")[-2]
    else:
        pswd = None
        url = link
    
    cget = create_scraper().request
    try:
        req = cget("post", url, data={"pass": pswd} if pswd else None)
        if req.status_code == 404:
            return "ERROR: File not found"
        
        soup = BeautifulSoup(req.content, "lxml")
        if btn := soup.find("a", {"class": "ok btn-general btn-orange"}):
            return btn["href"]
        return "ERROR: Failed to generate link"
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

def solidfiles(url: str) -> str:
    cget = create_scraper().request
    try:
        pageSource = cget("get", url, headers={"User-Agent": "Mozilla/5.0"}).text
        mainOptions = re.search(r"viewerOptions\'\,\ (.*?)\)\;", pageSource).group(1)
        return json.loads(mainOptions)["downloadUrl"]
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

def krakenfiles(url: str) -> str:
    sess = Session()
    try:
        res = sess.get(url)
        html = etree.HTML(res.text)
        post_url = f"https:{html.xpath('//form[@id=\"dl-form\"]/@action')[0]}"
        token = html.xpath('//input[@id="dl-token"]/@value')[0]
        dl_link = sess.post(post_url, data={"token": token}).json()
        return dl_link["url"]
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

def uploadee(url: str) -> str:
    cget = create_scraper().request
    try:
        soup = BeautifulSoup(cget("get", url).content, "lxml")
        sa = soup.find("a", attrs={"id": "d_l"})
        return sa["href"]
    except:
        return "ERROR: Failed to acquire download URL"

def mdisk(url: str) -> str:
    header = {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36",
    }
    id = url.split("/")[-1]
    return requests.get(
        f"https://diskuploader.entertainvideo.com/v1/file/cdnurl?param={id}",
        headers=header
    ).json()["source"]

def filepress(url: str) -> dict:
    cget = create_scraper().request
    try:
        url = cget("GET", url).url
        raw = urlparse(url)
        api = f"{raw.scheme}://{raw.hostname}/api/file/downlaod/"
        headers = {"Referer": f"{raw.scheme}://{raw.hostname}"}
        
        gd_res = cget("POST", api, headers=headers, json={
            "id": raw.path.split("/")[-1], 
            "method": "publicDownlaod"
        }).json()
        
        tg_res = cget("POST", api, headers=headers, json={
            "id": raw.path.split("/")[-1],
            "method": "telegramDownload"
        }).json()
        
        return {
            "google_drive": f'https://drive.google.com/uc?id={gd_res["data"]}' if "data" in gd_res else f'ERROR: {gd_res.get("statusText", "")}',
            "telegram": f'https://tghub.xyz/?start={tg_res["data"]}' if "data" in tg_res else "No Telegram file available"
        }
    except Exception as e:
        return {"error": f"ERROR: {e.__class__.__name__}"}

def gdtot(url: str) -> str:
    cget = create_scraper().request
    try:
        res = cget("GET", f'https://gdbot.xyz/file/{url.split("/")[-1]}')
        token_url = etree.HTML(res.content).xpath(
            "//a[contains(@class,'inline-flex items-center justify-center')]/@href"
        )[0]
        token_page = cget("GET", token_url)
        path = re.findall('\("(.*?)"\)', token_page.text)[0]
        raw = urlparse(token_url)
        return sharer_scraper(f"{raw.scheme}://{raw.hostname}{path}")
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

def sharer_scraper(url: str) -> str:
    cget = create_scraper().request
    try:
        url = cget("GET", url).url
        raw = urlparse(url)
        res = cget("GET", url, headers={"useragent": "Mozilla/5.0"})
        key = re.findall('"key",\s+"(.*?)"', res.text)[0]
        
        boundary = uuid4()
        headers = {
            "Content-Type": f"multipart/form-data; boundary=----WebKitFormBoundary{boundary}",
            "x-token": raw.hostname,
            "useragent": "Mozilla/5.0",
        }
        data = (
            f'------WebKitFormBoundary{boundary}\r\nContent-Disposition: form-data; name="action"\r\n\r\ndirect\r\n'
            f'------WebKitFormBoundary{boundary}\r\nContent-Disposition: form-data; name="key"\r\n\r\n{key}\r\n'
            f'------WebKitFormBoundary{boundary}--\r\n'
        )
        res = cget("POST", url, cookies=res.cookies, headers=headers, data=data).json()
        return res["url"]
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

def wetransfer(url: str) -> str:
    cget = create_scraper().request
    try:
        url = cget("GET", url).url
        res = cget("POST", 
            f'https://wetransfer.com/api/v4/transfers/{url.split("/")[-2]}/download',
            json={"security_hash": url.split("/")[-1], "intent": "entire_transfer"}
        ).json()
        return res.get("direct_link", f"ERROR: {res.get('message', 'Unknown error')}")
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

def akmfiles(url: str) -> str:
    cget = create_scraper().request
    try:
        url = cget("GET", url).url
        res = cget("POST", url, data={"op": "download2", "id": url.split("/")[-1]})
        html_tree = etree.HTML(res.content)
        direct_link = html_tree.xpath("//a[contains(@class,'btn btn-dow')]/@href")
        return direct_link[0] if direct_link else "ERROR: Direct link not found"
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

def shrdsk(url: str) -> str:
    cget = create_scraper().request
    try:
        url = cget("GET", url).url
        res = cget("GET", 
            f'https://us-central1-affiliate2apk.cloudfunctions.net/get_data?shortid={url.split("/")[-1]}'
        ).json()
        if res.get("type", "") == "upload" and "video_url" in res:
            return res["video_url"]
        return "ERROR: Direct link not found"
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

def linkbox(url: str) -> str:
    cget = create_scraper().request
    try:
        url = cget("GET", url).url
        res = cget("GET", 
            f'https://www.linkbox.to/api/file/detail?itemId={url.split("/")[-1]}'
        ).json()
        itemInfo = res["data"]["itemInfo"]
        name = quote(itemInfo["name"])
        raw = itemInfo["url"].split("/", 3)[-1]
        return f"https://wdl.nuplink.net/{raw}&filename={name}"
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

def zippyshare(url: str) -> str:
    cget = create_scraper().request
    try:
        url = cget("GET", url).url
        resp = cget("GET", url)
        if not resp.ok:
            return "ERROR: Failed to fetch page"
        
        js_script = etree.HTML(resp.text).xpath(
            "//script[contains(text(),'dlbutton')][3]/text()"
        )[0]
        
        uri1 = re.findall(r"\.href.=.\"/(.*?)/\"", js_script)[0]
        uri2 = re.findall(r"\+.\"/(.*?)\"", js_script)[0]
        domain = urlparse(url).hostname
        return f"https://{domain}/{uri1}/0/{uri2}"
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

def terabox(url: str) -> str:
    if not TERA_COOKIE:
        return "ERROR: Terabox cookies not configured"
    
    sess = Session()
    sess.cookies.update(TERA_COOKIE)
    try:
        res = sess.get(url)
        url = res.url
        key = url.split("?surl=")[-1]
        res = sess.get(f"https://www.terabox.com/wap/share/filelist?surl={key}")
        key = res.url.split("?surl=")[-1]
        soup = BeautifulSoup(res.content, "lxml")
        
        for fs in soup.find_all("script"):
            if fs.string and fs.string.startswith("try {eval(decodeURIComponent"):
                jsToken = fs.string.split("%22")[1]
                break
        else:
            return "ERROR: jsToken not found"
        
        res = sess.get(
            f"https://www.terabox.com/share/list?app_id=250528&jsToken={jsToken}&shorturl={key}&root=1"
        )
        result = res.json()
        
        if result["errno"] != 0:
            return f"ERROR: '{result['errmsg']}' Check cookies"
        
        result = result["list"][0]
        if result["isdir"] != "0":
            return "ERROR: Can't download folder"
        
        return result.get("dlink", "ERROR: Direct link not found")
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

# ======================== UNIVERSAL BYPASS ======================== #
def universal_bypass(url: str) -> str:
    domain = (urlparse(url).hostname or "").lower()
    
    # Service mapping
    service_map = {
        "yadi.sk": yandex_disk,
        "disk.yandex.com": yandex_disk,
        "mediafire.com": mediafire,
        "uptobox.com": uptobox,
        "osdn.net": osdn,
        "github.com": github,
        "hxfile.co": hxfile,
        "1drv.ms": onedrive,
        "pixeldrain.com": pixeldrain,
        "antfiles.com": antfiles,
        "streamtape.com": streamtape,
        "racaty.net": racaty,
        "1fichier.com": fichier,
        "solidfiles.com": solidfiles,
        "krakenfiles.com": krakenfiles,
        "upload.ee": uploadee,
        "akmfiles.com": akmfiles,
        "linkbox.to": linkbox,
        "shrdsk.me": shrdsk,
        "letsupload.io": letsupload,
        "zippyshare.com": zippyshare,
        "mdisk.me": mdisk,
        "wetransfer.com": wetransfer,
        "we.tl": wetransfer,
        "terabox.com": terabox,
        "teraboxapp.com": terabox,
        "4funbox.com": terabox,
        "nephobox.com": terabox,
        "mirrobox.com": terabox,
        "momerybox.com": terabox,
        "fembed.net": fembed,
        "fembed.com": fembed,
        "femax20.com": fembed,
        "fcdn.stream": fembed,
        "feurl.com": fembed,
        "layarkacaxxi.icu": fembed,
        "naniplay.com": fembed,
        "naniplay.nanime.biz": fembed,
        "naniplay.nanime.in": fembed,
        "mm9842.com": fembed,
        "sbembed.com": sbembed,
        "watchsb.com": sbembed,
        "streamsb.net": sbembed,
        "sbplay.org": sbembed,
    }
    
    # Special patterns
    if re.match(r"https?:\/\/.+\.gdtot\.\S+", url):
        return gdtot(url)
    
    if "filepress" in domain:
        return filepress(url).get("google_drive", "ERROR")
    
    # Find matching service
    for pattern, handler in service_map.items():
        if pattern in domain:
            return handler(url)
    
    return f"No handler found for URL: {url}"

# ======================== API ENDPOINTS ======================== #
def verify_token(token: str):
    if API_TOKEN and token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid API token")

@router.get("/universal")
async def universal_endpoint(
    url: str = Query(..., description="URL to bypass"),
    token: str = Query(None, description="Optional access token")
):
    """Universal bypass for 50+ file hosting services"""
    if API_TOKEN:
        verify_token(token or "")
    
    result = universal_bypass(url)
    if result.startswith("ERROR"):
        return {"success": False, "message": result}
    return {"success": True, "bypassed_url": result}

# Service-specific endpoints
services = {
    "mediafire": mediafire,
    "hxfile": hxfile,
    "letsupload": letsupload,
    "anonfiles": anonfilesBased,
    "fembed": fembed,
    "sbembed": sbembed,
    "onedrive": onedrive,
    "pixeldrain": pixeldrain,
    "antfiles": antfiles,
    "streamtape": streamtape,
    "racaty": racaty,
    "fichier": fichier,
    "solidfiles": solidfiles,
    "krakenfiles": krakenfiles,
    "uploadee": uploadee,
    "filepress": lambda url: filepress(url).get("google_drive", "ERROR"),
    "gdtot": gdtot,
    "sharer": sharer_scraper,
    "wetransfer": wetransfer,
    "akmfiles": akmfiles,
    "shrdsk": shrdsk,
    "linkbox": linkbox,
    "zippyshare": zippyshare,
    "mdisk": mdisk,
    "terabox": terabox,
}

for service, handler in services.items():
    @router.get(f"/{service}")
    async def service_endpoint(
        url: str = Query(..., description=f"{service.capitalize()} URL"),
        token: str = Query(None, description="Optional access token"),
        handler=handler
    ):
        if API_TOKEN:
            verify_token(token or "")
        
        result = handler(url)
        if isinstance(result, dict):
            return {"success": True, **result}
        if result.startswith("ERROR"):
            return {"success": False, "message": result}
        return {"success": True, "bypassed_url": result}

@router.get("/supported_services")
async def supported_services():
    """List all supported services"""
    return {
        "success": True,
        "services": sorted(services.keys()) + ["universal"],
        "count": len(services) + 1
    }