from fastapi import APIRouter, Query
from urllib.parse import quote_plus, urlparse
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

router = APIRouter()
logger = logging.getLogger(__name__)

# ======================== BYPASS FUNCTIONS ======================== #

# Linkvertise bypass
async def bypass(url: str) -> str:
    try:
        encoded_url = quote_plus(url)
        api_url = f"https://iwoozie.baby/api/free/bypass?url={encoded_url}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Referer": "https://thebypasser.com/",
            "Origin": "https://thebypasser.com",
            "Accept": "*/*",
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                api_url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Bypass API error: {response.status} - {error_text}")
                    raise ValueError(f"API returned {response.status}")
                
                data = await response.json()
                if not data.get("success") or not data.get("result"):
                    raise ValueError("Invalid API response format")
                
                return data["result"]
                
    except Exception as e:
        logger.exception("Bypass failed")
        raise HTTPException(status_code=400, detail=f"Bypass failed: {str(e)}")

# Mediafire bypass
def mediafire(url: str) -> str:
    direct_pattern = r"https?:\/\/download\d+\.mediafire\.com\/\S+\/\S+\/\S+"
    final_link = re.findall(direct_pattern, url)
    if final_link:
        return final_link[0]

    cget = create_scraper().request
    try:
        url = cget("get", url).url
        page = cget("get", url).text
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

    final_link = re.findall(r"\'(" + direct_pattern + r")\'", page)
    if not final_link:
        return "ERROR: No links found in this page"

    return final_link[0]

# Hxfile bypass
def hxfile(url: str) -> str:
    sess = Session()
    try:
        headers = {
            "content-type": "application/x-www-form-urlencoded",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.152 Safari/537.36",
        }

        file_id = urlparse(url).path.strip("/")
        data = {
            "op": "download2",
            "id": file_id,
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

# Letsupload bypass
def letsupload(url: str) -> str:
    scraper = create_scraper()
    try:
        res = scraper.post(url)
        text = res.text
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

    match = re.findall(r'(https?://letsupload\.io\/[^\s"\']+)', text)
    if match:
        return match[0]

    return "ERROR: Direct Link not found"

# Anonfiles bypass
def anonfilesBased(url: str) -> str:
    cget = create_scraper().request
    try:
        soup = BeautifulSoup(cget("get", url).content, "lxml")
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"
    sa = soup.find(id="download-url")
    if sa:
        return sa["href"]
    return "ERROR: File not found!"

# Fembed bypass
def fembed(link: str) -> str:
    sess = Session()
    try:
        link = link.replace("/v/", "/f/")
        raw = sess.get(link)
        api = re.search(r"(/api/source/[^\"']+)", raw.text)
        if api is not None:
            result = {}
            raw = sess.post("https://layarkacaxxi.icu" + api.group(1)).json()
            for d in raw["data"]:
                f = d["file"]
                head = sess.head(f)
                direct = head.headers.get("Location", link)
                result[f"{d['label']}/{d['type']}"] = direct
            dl_url = result
            count = len(dl_url)
            lst_link = [dl_url[i] for i in dl_url]
            return lst_link[count - 1]
        return "ERROR: No source API found"
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

# Sbembed bypass
def sbembed(link: str) -> str:
    sess = Session()
    try:
        raw = sess.get(link).text
        soup = BeautifulSoup(raw, "html.parser")
        result = {}
        for a in soup.findAll("a", onclick=re.compile(r"^download_video[^>]+")):
            data = dict(
                zip(["id", "mode", "hash"], re.findall(r"[\"']([^\"']+)[\"']", a["onclick"]))
            )
            data["op"] = "download_orig"
            raw = sess.get("https://sbembed.com/dl", params=data)
            soup = BeautifulSoup(raw.text, "html.parser")
            if direct := soup.find("a", text=re.compile("(?i)^direct")):
                result[a.text] = direct["href"]
        if result:
            lst_link = list(result.values())
            return lst_link[-1]
        return "ERROR: Direct link not found"
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

# Onedrive bypass
def onedrive(link: str) -> str:
    link_without_query = urlparse(link)._replace(query=None).geturl()
    direct_link_encoded = str(
        standard_b64encode(bytes(link_without_query, "utf-8")), "utf-8"
    )
    direct_link1 = f"https://api.onedrive.com/v1.0/shares/u!{direct_link_encoded}/root/content"
    cget = create_scraper().request
    try:
        resp = cget("head", direct_link1)
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"
    if resp.status_code != 302:
        return "ERROR: Unauthorized link, may be private"
    return resp.next.url

# Pixeldrain bypass
def pixeldrain(url: str) -> str:
    url = url.strip("/ ")
    file_id = url.split("/")[-1]
    if url.split("/")[-2] == "l":
        info_link = f"https://pixeldrain.com/api/list/{file_id}"
        dl_link = f"https://pixeldrain.com/api/list/{file_id}/zip?download"
    else:
        info_link = f"https://pixeldrain.com/api/file/{file_id}/info"
        dl_link = f"https://pixeldrain.com/api/file/{file_id}?download"
    cget = create_scraper().request
    try:
        resp = cget("get", info_link).json()
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"
    if resp.get("success"):
        return dl_link
    else:
        return f"ERROR: {resp.get('message', 'Failed')}"

# Antfiles bypass
def antfiles(url: str) -> str:
    sess = Session()
    try:
        raw = sess.get(url).text
        soup = BeautifulSoup(raw, "html.parser")
        if a := soup.find(class_="main-btn", href=True):
            return "{0.scheme}://{0.netloc}/{1}".format(urlparse(url), a["href"])
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

# Streamtape bypass
def streamtape(url: str) -> str:
    response = requests.get(url)
    if videolink := re.findall(r"document.*((?=id\=)[^\"']+)", response.text):
        return "https://streamtape.com/get_video?" + videolink[-1]
    return "ERROR: Direct link not found"

# Racaty bypass
def racaty(url: str) -> str:
    cget = create_scraper().request
    try:
        url = cget("GET", url).url
        json_data = {"op": "download2", "id": url.split("/")[-1]}
        res = cget("POST", url, data=json_data)
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"
    html_tree = etree.HTML(res.text)
    direct_link = html_tree.xpath("//a[contains(@id,'uniqueExpirylink')]/@href")
    return direct_link[0] if direct_link else "ERROR: Direct link not found"

# Fichier bypass
def fichier(link: str) -> str:
    regex = r"^([http:\/\/|https:\/\/]+)?.*1fichier\.com\/\?.+"
    gan = re.match(regex, link)
    if not gan:
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
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"
    if req.status_code == 404:
        return "ERROR: File not found"
    soup = BeautifulSoup(req.content, "lxml")
    if soup.find("a", {"class": "ok btn-general btn-orange"}):
        return soup.find("a", {"class": "ok btn-general btn-orange"})["href"]
    return "ERROR: Failed to generate link"

# Solidfiles bypass
def solidfiles(url: str) -> str:
    cget = create_scraper().request
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        pageSource = cget("get", url, headers=headers).text
        mainOptions = re.search(r"viewerOptions\'\,\ (.*?)\)\;", pageSource).group(1)
        return json.loads(mainOptions)["downloadUrl"]
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

# Krakenfiles bypass
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

# Uploadee bypass
def uploadee(url: str) -> str:
    cget = create_scraper().request
    try:
        soup = BeautifulSoup(cget("get", url).content, "lxml")
        sa = soup.find("a", attrs={"id": "d_l"})
        return sa["href"]
    except Exception:
        return f"ERROR: Failed to acquire download URL from upload.ee"

# Filepress bypass
def filepress(url: str) -> dict:
    cget = create_scraper().request
    try:
        url = cget("GET", url).url
        raw = urlparse(url)
        gd_data = {"id": raw.path.split("/")[-1], "method": "publicDownlaod"}
        tg_data = {"id": raw.path.split("/")[-1], "method": "telegramDownload"}
        api = f"{raw.scheme}://{raw.hostname}/api/file/downlaod/"
        headers = {"Referer": f"{raw.scheme}://{raw.hostname}"}
        
        gd_res = cget("POST", api, headers=headers, json=gd_data).json()
        tg_res = cget("POST", api, headers=headers, json=tg_data).json()
        
        gd_result = f'https://drive.google.com/uc?id={gd_res["data"]}' if "data" in gd_res else f'ERROR: {gd_res["statusText"]}'
        tg_result = f'https://tghub.xyz/?start={tg_res["data"]}' if "data" in tg_res else "No Telegram file available"
        
        return {
            "google_drive": gd_result,
            "telegram": tg_result
        }
    except Exception as e:
        return {"error": f"ERROR: {e.__class__.__name__}"}

# Gdtot bypass
def gdtot(url: str) -> str:
    cget = create_scraper().request
    try:
        res = cget("GET", f'https://gdbot.xyz/file/{url.split("/")[-1]}')
        token_url = etree.HTML(res.content).xpath(
            "//a[contains(@class,'inline-flex items-center justify-center')]/@href"
        )
        if not token_url:
            return "ERROR: Cannot bypass"
        token_url = token_url[0]
        token_page = cget("GET", token_url)
        path = re.findall('\("(.*?)"\)', token_page.text)
        if not path:
            return "ERROR: Cannot bypass"
        path = path[0]
        raw = urlparse(token_url)
        final_url = f"{raw.scheme}://{raw.hostname}{path}"
        return sharer_scraper(final_url)
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

# Sharer scraper
def sharer_scraper(url: str) -> str:
    cget = create_scraper().request
    try:
        url = cget("GET", url).url
        raw = urlparse(url)
        header = {"useragent": "Mozilla/5.0"}
        res = cget("GET", url, headers=header)
        key = re.findall('"key",\s+"(.*?)"', res.text)
        if not key:
            return "ERROR: Key not found!"
        key = key[0]
        
        if not etree.HTML(res.content).xpath("//button[@id='drc']"):
            return "ERROR: No direct download button"
            
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
        return res["url"] if "url" in res else "ERROR: Drive Link not found"
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

# Wetransfer bypass
def wetransfer(url: str) -> str:
    cget = create_scraper().request
    try:
        url = cget("GET", url).url
        json_data = {"security_hash": url.split("/")[-1], "intent": "entire_transfer"}
        res = cget("POST", f'https://wetransfer.com/api/v4/transfers/{url.split("/")[-2]}/download', json=json_data).json()
        return res["direct_link"] if "direct_link" in res else f"ERROR: {res.get('message', 'Unknown error')}"
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

# AKMFiles bypass
def akmfiles(url: str) -> str:
    cget = create_scraper().request
    try:
        url = cget("GET", url).url
        json_data = {"op": "download2", "id": url.split("/")[-1]}
        res = cget("POST", url, data=json_data)
        html_tree = etree.HTML(res.content)
        direct_link = html_tree.xpath("//a[contains(@class,'btn btn-dow')]/@href")
        return direct_link[0] if direct_link else "ERROR: Direct link not found"
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

# Shrdsk bypass
def shrdsk(url: str) -> str:
    cget = create_scraper().request
    try:
        url = cget("GET", url).url
        res = cget("GET", f'https://us-central1-affiliate2apk.cloudfunctions.net/get_data?shortid={url.split("/")[-1]}')
        if res.status_code != 200:
            return f"ERROR: Status Code {res.status_code}"
        res = res.json()
        if "type" in res and res["type"].lower() == "upload" and "video_url" in res:
            return res["video_url"]
        return "ERROR: cannot find direct link"
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

# Linkbox bypass
def linkbox(url: str) -> str:
    cget = create_scraper().request
    try:
        url = cget("GET", url).url
        res = cget("GET", f'https://www.linkbox.to/api/file/detail?itemId={url.split("/")[-1]}').json()
        if "data" not in res or not res["data"] or "itemInfo" not in res["data"]:
            return "ERROR: Invalid response"
        itemInfo = res["data"]["itemInfo"]
        name = quote(itemInfo["name"])
        raw = itemInfo["url"].split("/", 3)[-1]
        return f"https://wdl.nuplink.net/{raw}&filename={name}"
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

# Zippyshare bypass
def zippyshare(url: str) -> str:
    cget = create_scraper().request
    try:
        url = cget("GET", url).url
        resp = cget("GET", url)
        if not resp.ok:
            return "ERROR: Failed to fetch page"
        pages = etree.HTML(resp.text).xpath("//script[contains(text(),'dlbutton')][3]/text()")
        if not pages:
            return "ERROR: Script not found"
        js_script = pages[0]
        uri1 = re.findall(r"\.href.=.\"/(.*?)/\"", js_script)
        uri2 = re.findall(r"\+.\"/(.*?)\"", js_script)
        if not uri1 or not uri2:
            return "ERROR: URL parts not found"
        domain = urlparse(url).hostname
        return f"https://{domain}/{uri1[0]}/0/{uri2[0]}"
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"


      
def yandex_disk(url: str) -> str:
    """Yandex.Disk direct link generator"""
    try:
        api = "https://cloud-api.yandex.net/v1/disk/public/resources/download?public_key={}"
        cget = create_scraper().request
        return cget("get", api.format(url)).json()["href"]
    except:
        return "ERROR: File not found/Download limit reached"

def uptobox(url: str) -> str:
    """Uptobox direct link generator"""
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
            sleep(res["data"]["waiting"])
            res = cget("get", f"{file_link}&waitingToken={waiting_token}").json()
            return res["data"]["dlLink"]
        elif res["statusCode"] == 39:
            wait_time = get_readable_time(res['data']['waiting'])
            return f"ERROR: Uptobox is being limited please wait {wait_time}"
        else:
            return f"ERROR: {res['message']}"
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

      

# ======================== API ENDPOINTS ======================== #

@router.get("/linkvertise")
async def linkvertise_endpoint(url: str = Query(..., description="Linkvertise URL")):
    result = await bypass(url)
    return {"success": True, "bypassed_url": result}

@router.get("/mediafire")
def mediafire_endpoint(url: str = Query(..., description="Mediafire URL")):
    result = mediafire(url)
    return {"success": True, "bypassed_url": result}  

@router.get("/hxfile")
def hxfile_endpoint(url: str = Query(..., description="Hxfile URL")):
    result = hxfile(url)
    return {"success": True, "bypassed_url": result}

@router.get("/letsupload")
def letsupload_endpoint(url: str = Query(..., description="LetsUpload URL")):
    result = letsupload(url)
    return {"success": True, "bypassed_url": result}

@router.get("/anonfiles")
def anonfiles_endpoint(url: str = Query(..., description="Anonfiles URL")):
    result = anonfilesBased(url)
    return {"success": True, "bypassed_url": result}

@router.get("/fembed")
def fembed_endpoint(url: str = Query(..., description="Fembed URL")):
    result = fembed(url)
    return {"success": True, "bypassed_url": result}

@router.get("/sbembed")
def sbembed_endpoint(url: str = Query(..., description="Sbembed URL")):
    result = sbembed(url)
    return {"success": True, "bypassed_url": result}

@router.get("/onedrive")
def onedrive_endpoint(url: str = Query(..., description="OneDrive URL")):
    result = onedrive(url)
    return {"success": True, "bypassed_url": result}

@router.get("/pixeldrain")
def pixeldrain_endpoint(url: str = Query(..., description="Pixeldrain URL")):
    result = pixeldrain(url)
    return {"success": True, "bypassed_url": result}

@router.get("/antfiles")
def antfiles_endpoint(url: str = Query(..., description="Antfiles URL")):
    result = antfiles(url)
    return {"success": True, "bypassed_url": result}

@router.get("/streamtape")
def streamtape_endpoint(url: str = Query(..., description="Streamtape URL")):
    result = streamtape(url)
    return {"success": True, "bypassed_url": result}

@router.get("/racaty")
def racaty_endpoint(url: str = Query(..., description="Racaty URL")):
    result = racaty(url)
    return {"success": True, "bypassed_url": result}

@router.get("/fichier")
def fichier_endpoint(url: str = Query(..., description="1Fichier URL")):
    result = fichier(url)
    return {"success": True, "bypassed_url": result}

@router.get("/solidfiles")
def solidfiles_endpoint(url: str = Query(..., description="Solidfiles URL")):
    result = solidfiles(url)
    return {"success": True, "bypassed_url": result}

@router.get("/krakenfiles")
def krakenfiles_endpoint(url: str = Query(..., description="Krakenfiles URL")):
    result = krakenfiles(url)
    return {"success": True, "bypassed_url": result}

@router.get("/uploadee")
def uploadee_endpoint(url: str = Query(..., description="Upload.ee URL")):
    result = uploadee(url)
    return {"success": True, "bypassed_url": result}

@router.get("/filepress")
def filepress_endpoint(url: str = Query(..., description="FilePress URL")):
    result = filepress(url)
    if "error" in result:
        return {"success": False, "message": result["error"]}
    return {"success": True, "bypassed_urls": result}

@router.get("/gdtot")
def gdtot_endpoint(url: str = Query(..., description="GDTOT URL")):
    result = gdtot(url)
    if result.startswith("ERROR:"):
        return {"success": False, "message": result}
    return {"success": True, "bypassed_url": result}

@router.get("/sharer")
def sharer_endpoint(url: str = Query(..., description="Sharer URL")):
    result = sharer_scraper(url)
    if result.startswith("ERROR:"):
        return {"success": False, "message": result}
    return {"success": True, "bypassed_url": result}

@router.get("/wetransfer")
def wetransfer_endpoint(url: str = Query(..., description="WeTransfer URL")):
    result = wetransfer(url)
    if result.startswith("ERROR:"):
        return {"success": False, "message": result}
    return {"success": True, "bypassed_url": result}

@router.get("/akmfiles")
def akmfiles_endpoint(url: str = Query(..., description="AKMFiles URL")):
    result = akmfiles(url)
    if result.startswith("ERROR:"):
        return {"success": False, "message": result}
    return {"success": True, "bypassed_url": result}

@router.get("/shrdsk")
def shrdsk_endpoint(url: str = Query(..., description="Shrdsk URL")):
    result = shrdsk(url)
    if result.startswith("ERROR:"):
        return {"success": False, "message": result}
    return {"success": True, "bypassed_url": result}

@router.get("/linkbox")
def linkbox(url: str = Query(..., description="LinkBox URL")):
    result = linkbox(url)
    if result.startswith("ERROR:"):
        return {"success": False, "message": result}
    return {"success": True, "bypassed_url": result}

@router.get("/zippyshare")
def zippyshare(url: str = Query(..., description="ZippyShare URL")):
    result = zippyshare(url)
    if result.startswith("ERROR:"):
        return {"success": False, "message": result}
    return {"success": True, "bypassed_url": result}

@router.get("/yandexdisk")
def yandex_disk(url: str = Query(..., description="ZippyShare URL")):
    result = yandex_disk(url)
    if result.startswith("ERROR:"):
        return {"success": False, "message": result}
    return {"success": True, "bypassed_url": result}

  