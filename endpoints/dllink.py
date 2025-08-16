"""
DLLink endpoint - Direct download link extraction for various platforms
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from urllib.parse import urlparse, parse_qs
from uuid import uuid4
from base64 import b64decode
from re import findall, DOTALL
from requests import Session
from cloudscraper import create_scraper
from bs4 import BeautifulSoup
from lxml import etree
from aiohttp import ClientSession
from fastapi import APIRouter, Query, HTTPException, status
from fastapi.responses import JSONResponse

from config import Config

logger = logging.getLogger(__name__)
router = APIRouter()

class DDLException(Exception):
    """Custom exception for DDL operations"""
    pass

def get_dl(drive_url: str) -> str:
    """Generate direct index link if configured"""
    if not Config.DIRECT_INDEX:
        return drive_url
    try:
        file_id = drive_url.split('/d/')[1].split('/')[0] if '/d/' in drive_url else drive_url.split('id=')[1].split('&')[0]
        return f"{Config.DIRECT_INDEX}/0:{file_id}"
    except:
        return drive_url

async def filepress_scraper(url: str) -> str:
    """FilePress scraper with async support"""
    cget = create_scraper().request
    try:
        url = cget("GET", url).url
        raw = urlparse(url)
        
        async with ClientSession() as sess:
            json_data = {
                "id": raw.path.split("/")[-1],
                "method": "publicDownlaod",
            }
            
            # Remove method for telegram endpoint
            del json_data["method"]
            
            async with sess.post(
                f"{raw.scheme}://{raw.hostname}/api/file/telegram/downlaod/",
                headers={"Referer": f"{raw.scheme}://{raw.hostname}"},
                json=json_data,
            ) as resp:
                tg_id = await resp.json()
                
            if tg_id.get("data", False):
                t_url = f"https://tghub.xyz/?start={tg_id['data']}"
                bot_name = findall(
                    "filepress_[a-zA-Z0-9]+_bot", cget("GET", t_url).text
                )[0]
                tg_link = f"https://t.me/{bot_name}/?start={tg_id['data']}"
            else:
                tg_link = (
                    "Unavailable"
                    if tg_id["statusText"] == "Ok"
                    else tg_id["statusText"]
                )
                
    except Exception as e:
        raise DDLException(f"{e.__class__.__name__}")
        
    if tg_link == "Unavailable":
        tg_link_text = "Unavailable"
    else:
        tg_link_text = f'<a href="{tg_link}">Click Here</a>'

    parse_txt = f"""┏<b>FilePress:</b> <a href="{url}">Click Here</a>
┗<b>Telegram:</b> {tg_link_text}"""
    
    return parse_txt

async def gdtot_scraper(url: str) -> str:
    """GDToT scraper with improved error handling"""
    cget = create_scraper().request
    try:
        url = cget("GET", url).url
        p_url = urlparse(url)
        res = cget(
            "POST",
            f"{p_url.scheme}://{p_url.hostname}/ddl",
            data={"dl": str(url.split("/")[-1])},
        )
    except Exception as e:
        raise DDLException(f"{e.__class__.__name__}")
        
    if (
        drive_link := findall(r"myDl\('(.*?)'\)", res.text)
    ) and "drive.google.com" in drive_link[0]:
        d_link = drive_link[0]
    elif Config.GDTOT_CRYPT:
        cget("GET", url, cookies={"crypt": Config.GDTOT_CRYPT})
        p_url = urlparse(url)
        js_script = cget(
            "POST",
            f"{p_url.scheme}://{p_url.hostname}/dld",
            data={"dwnld": url.split("/")[-1]},
        )
        g_id = findall("gd=(.*?)&", js_script.text)
        try:
            decoded_id = b64decode(str(g_id[0])).decode("utf-8")
        except:
            raise DDLException(
                "Try in your browser, mostly file not found or user limit exceeded!"
            )
        d_link = f"https://drive.google.com/open?id={decoded_id}"
    else:
        raise DDLException(
            "Drive Link not found, Try in your browser! GDTOT_CRYPT not Provided!"
        )
        
    soup = BeautifulSoup(cget("GET", url).content, "html.parser")
    parse_data = (
        (soup.select('meta[property^="og:description"]')[0]["content"])
        .replace("Download ", "")
        .rsplit("-", maxsplit=1)
    )
    parse_txt = f"""┏<b>Name:</b> <code>{parse_data[0]}</code>
┠<b>Size:</b> <code>{parse_data[-1]}</code>
┠<b>GDToT:</b> <a href="{url}">Click Here</a>
"""
    if Config.DIRECT_INDEX:
        parse_txt += f"┠<b>Temp Index:</b> <a href='{get_dl(d_link)}'>Click Here</a>\n"
    parse_txt += f"┗<b>GDrive:</b> <a href='{d_link}'>Click Here</a>"
    return parse_txt

async def drivescript_scraper(url: str, crypt: str, dtype: str) -> str:
    """DriveScript scraper for HubDrive, KatDrive, DriveFire"""
    rs = Session()
    resp = rs.get(url)
    title = findall(r">(.*?)<\/h4>", resp.text)[0]
    size = findall(r">(.*?)<\/td>", resp.text)[1]
    p_url = urlparse(url)

    dlink = ""
    if dtype != "DriveFire":
        try:
            js_query = rs.post(
                f"{p_url.scheme}://{p_url.hostname}/ajax.php?ajax=direct-download",
                data={"id": str(url.split("/")[-1])},
                headers={"x-requested-with": "XMLHttpRequest"},
            ).json()
            if str(js_query["code"]) == "200":
                dlink = f"{p_url.scheme}://{p_url.hostname}{js_query['file']}"
        except Exception as e:
            logger.error(e)

    if not dlink and crypt:
        rs.get(url, cookies={"crypt": crypt})
        try:
            js_query = rs.post(
                f"{p_url.scheme}://{p_url.hostname}/ajax.php?ajax=download",
                data={"id": str(url.split("/")[-1])},
                headers={"x-requested-with": "XMLHttpRequest"},
            ).json()
        except Exception as e:
            raise DDLException(f"{e.__class__.__name__}")
        if str(js_query["code"]) == "200":
            dlink = f"{p_url.scheme}://{p_url.hostname}{js_query['file']}"

    if dlink:
        res = rs.get(dlink)
        soup = BeautifulSoup(res.text, "html.parser")
        gd_data = soup.select('a[class="btn btn-primary btn-user"]')
        parse_txt = f"""┏<b>Name:</b> <code>{title}</code>
┠<b>Size:</b> <code>{size}</code>
┠<b>{dtype}:</b> <a href="{url}">Click Here</a>"""
        if dtype == "HubDrive":
            parse_txt += (
                f"""\n┠<b>Instant:</b> <a href="{gd_data[1]['href']}">Click Here</a>"""
            )
        if (d_link := gd_data[0]["href"]) and Config.DIRECT_INDEX:
            parse_txt += (
                f"\n┠<b>Temp Index:</b> <a href='{get_dl(d_link)}'>Click Here</a>"
            )
        parse_txt += f"\n┗<b>GDrive:</b> <a href='{d_link}'>Click Here</a>"
        return parse_txt
    elif not dlink and not crypt:
        raise DDLException(
            f"{dtype} Crypt Not Provided and Direct Link Generate Failed"
        )
    else:
        raise DDLException(f'{js_query["file"]}')

async def appflix_single(url: str) -> str:
    """Single AppFlix file scraper"""
    cget = create_scraper().request
    url = cget("GET", url).url
    soup = BeautifulSoup(
        cget("GET", url, allow_redirects=False).text, "html.parser"
    )
    ss = soup.select("li[class^='list-group-item']")
    dbotv2 = (
        dbot[0]["href"]
        if "gdflix" in url and (dbot := soup.select("a[href*='drivebot.lol']"))
        else None
    )
    try:
        d_link = await sharer_scraper_internal(url)
    except Exception as e:
        if not dbotv2:
            raise DDLException(e)
        else:
            d_link = str(e)
            
    parse_txt = f"""┏<b>Name:</b> <code>{ss[0].string.split(":")[1]}</code>
┠<b>Size:</b> <code>{ss[2].string.split(":")[1]}</code>
┠<b>Source:</b> <code>{url}</code>"""
    if dbotv2:
        parse_txt += f"\n┠<b>DriveBot V2:</b> <a href='{dbotv2}'>Click Here</a>"
    if d_link and Config.DIRECT_INDEX:
        parse_txt += (
            f"\n┠<b>Temp Index:</b> <a href='{get_dl(d_link)}'>Click Here</a>"
        )
    parse_txt += f"\n┗<b>GDrive:</b> <a href='{d_link}'>Click Here</a>"
    return parse_txt

async def appflix_scraper(url: str) -> str:
    """AppFlix scraper with pack support"""
    if "/pack/" in url:
        cget = create_scraper().request
        url = cget("GET", url).url
        soup = BeautifulSoup(cget("GET", url).content, "html.parser")
        p_url = urlparse(url)
        body = ""
        
        atasks = [
            asyncio.create_task(
                appflix_single(f"{p_url.scheme}://{p_url.hostname}" + ss["href"])
            )
            for ss in soup.select("a[href^='/file/']")
        ]
        completed_tasks = await asyncio.gather(*atasks, return_exceptions=True)
        
        for bp_link in completed_tasks:
            if isinstance(bp_link, Exception):
                body += "\n\n" + f"<b>Error:</b> {bp_link}"
            else:
                body += "\n\n" + bp_link
                
        return f"""┏<b>Name:</b> <code>{soup.title.string}</code>
┗<b>Source:</b> <code>{url}</code>{body}"""
    
    return await appflix_single(url)

async def sharerpw_scraper(url: str, force: bool = False) -> str:
    """SharerPW scraper with authentication"""
    if not Config.XSRF_TOKEN and not Config.LARAVEL_SESSION:
        raise DDLException("XSRF_TOKEN or LARAVEL_SESSION not Provided!")
        
    cget = create_scraper(allow_brotli=False).request
    resp = cget(
        "GET",
        url,
        cookies={
            "XSRF-TOKEN": Config.XSRF_TOKEN,
            "laravel_session": Config.LARAVEL_SESSION,
        },
    )
    parse_txt = findall(">(.*?)<\/td>", resp.text)
    ddl_btn = etree.HTML(resp.content).xpath("//button[@id='btndirect']")
    token = findall("_token\s=\s'(.*?)'", resp.text, DOTALL)[0]
    data = {"_token": token}
    if not force:
        data["nl"] = 1
        
    headers = {
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "x-requested-with": "XMLHttpRequest",
    }
    
    try:
        res = cget("POST", url + "/dl", headers=headers, data=data).json()
    except Exception as e:
        raise DDLException(str(e))
        
    parse_data = f"""┏<b>Name:</b> <code>{parse_txt[2]}</code>
┠<b>Size:</b> <code>{parse_txt[8]}</code>
┠<b>Added On:</b> <code>{parse_txt[11]}</code>
"""
    if res["status"] == 0:
        if Config.DIRECT_INDEX:
            parse_data += (
                f"\n┠<b>Temp Index:</b> <a href='{get_dl(res['url'])}'>Click Here</a>"
            )
        return parse_data + f"\n┗<b>GDrive:</b> <a href='{res['url']}'>Click Here</a>"
    elif res["status"] == 2:
        msg = res["message"].replace("<br/>", "\n")
        return parse_data + f"\n┗<b>Error:</b> {msg}"
        
    if len(ddl_btn) and not force:
        return await sharerpw_scraper(url, force=True)

async def sharer_scraper_internal(url: str) -> str:
    """Internal sharer scraper function"""
    cget = create_scraper().request
    try:
        url = cget("GET", url).url
        raw = urlparse(url)
        header = {
            "useragent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/534.10 (KHTML, like Gecko) Chrome/7.0.548.0 Safari/534.10"
        }
        res = cget("GET", url, headers=header)
    except Exception as e:
        raise DDLException(f"{e.__class__.__name__}")
        
    key = findall('"key",\s+"(.*?)"', res.text)
    if not key:
        raise DDLException("Download Link Key not found!")
    key = key[0]
    
    if not etree.HTML(res.content).xpath("//button[@id='drc']"):
        raise DDLException("Link don't have direct download button")
        
    boundary = uuid4()
    headers = {
        "Content-Type": f"multipart/form-data; boundary=----WebKitFormBoundary{boundary}",
        "x-token": raw.hostname,
        "useragent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/534.10 (KHTML, like Gecko) Chrome/7.0.548.0 Safari/534.10",
    }

    data = (
        f'------WebKitFormBoundary{boundary}\r\nContent-Disposition: form-data; name="action"\r\n\r\ndirect\r\n'
        f'------WebKitFormBoundary{boundary}\r\nContent-Disposition: form-data; name="key"\r\n\r\n{key}\r\n'
        f'------WebKitFormBoundary{boundary}\r\nContent-Disposition: form-data; name="action_token"\r\n\r\n\r\n'
        f"------WebKitFormBoundary{boundary}--\r\n"
    )
    
    try:
        res = cget("POST", url, cookies=res.cookies, headers=headers, data=data).json()
    except Exception as e:
        raise DDLException(f"{e.__class__.__name__}")
        
    if "url" not in res:
        raise DDLException("Drive Link not found, Try in your browser")
        
    if "drive.google.com" in res["url"]:
        return res["url"]
        
    try:
        res = cget("GET", res["url"])
    except Exception as e:
        raise DDLException(f"ERROR: {e.__class__.__name__}")
        
    if (
        drive_link := etree.HTML(res.content).xpath("//a[contains(@class,'btn')]/@href")
    ) and "drive.google.com" in drive_link[0]:
        return drive_link[0]
    else:
        raise DDLException("Drive Link not found, Try in your browser")

# ======================== API ENDPOINTS ======================== #

@router.get("/filepress")
async def filepress_endpoint(url: str = Query(..., description="FilePress URL")):
    """Extract download links from FilePress"""
    try:
        result = await filepress_scraper(url)
        return JSONResponse({
            "success": True,
            "source": "FilePress",
            "data": result,
            "url": url
        })
    except DDLException as e:
        logger.error(f"FilePress error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"FilePress extraction failed: {str(e)}"
        )
    except Exception as e:
        logger.exception(f"Unexpected FilePress error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}"
        )

@router.get("/gdtot")
async def gdtot_endpoint(url: str = Query(..., description="GDToT URL")):
    """Extract download links from GDToT"""
    try:
        result = await gdtot_scraper(url)
        return JSONResponse({
            "success": True,
            "source": "GDToT",
            "data": result,
            "url": url
        })
    except DDLException as e:
        logger.error(f"GDToT error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"GDToT extraction failed: {str(e)}"
        )
    except Exception as e:
        logger.exception(f"Unexpected GDToT error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}"
        )

@router.get("/hubdrive")
async def hubdrive_endpoint(url: str = Query(..., description="HubDrive URL")):
    """Extract download links from HubDrive"""
    try:
        result = await drivescript_scraper(url, Config.HUBDRIVE_CRYPT, "HubDrive")
        return JSONResponse({
            "success": True,
            "source": "HubDrive",
            "data": result,
            "url": url
        })
    except DDLException as e:
        logger.error(f"HubDrive error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"HubDrive extraction failed: {str(e)}"
        )
    except Exception as e:
        logger.exception(f"Unexpected HubDrive error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}"
        )

@router.get("/katdrive")
async def katdrive_endpoint(url: str = Query(..., description="KatDrive URL")):
    """Extract download links from KatDrive"""
    try:
        result = await drivescript_scraper(url, Config.KATDRIVE_CRYPT, "KatDrive")
        return JSONResponse({
            "success": True,
            "source": "KatDrive",
            "data": result,
            "url": url
        })
    except DDLException as e:
        logger.error(f"KatDrive error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"KatDrive extraction failed: {str(e)}"
        )
    except Exception as e:
        logger.exception(f"Unexpected KatDrive error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}"
        )

@router.get("/drivefire")
async def drivefire_endpoint(url: str = Query(..., description="DriveFire URL")):
    """Extract download links from DriveFire"""
    try:
        result = await drivescript_scraper(url, Config.DRIVEFIRE_CRYPT, "DriveFire")
        return JSONResponse({
            "success": True,
            "source": "DriveFire",
            "data": result,
            "url": url
        })
    except DDLException as e:
        logger.error(f"DriveFire error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"DriveFire extraction failed: {str(e)}"
        )
    except Exception as e:
        logger.exception(f"Unexpected DriveFire error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}"
        )

@router.get("/appflix")
async def appflix_endpoint(url: str = Query(..., description="AppFlix/GDFlix URL")):
    """Extract download links from AppFlix/GDFlix"""
    try:
        result = await appflix_scraper(url)
        return JSONResponse({
            "success": True,
            "source": "AppFlix",
            "data": result,
            "url": url
        })
    except DDLException as e:
        logger.error(f"AppFlix error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"AppFlix extraction failed: {str(e)}"
        )
    except Exception as e:
        logger.exception(f"Unexpected AppFlix error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}"
        )

@router.get("/sharerpw")
async def sharerpw_endpoint(
    url: str = Query(..., description="SharerPW URL"),
    force: bool = Query(False, description="Force direct download")
):
    """Extract download links from SharerPW"""
    try:
        result = await sharerpw_scraper(url, force)
        return JSONResponse({
            "success": True,
            "source": "SharerPW",
            "data": result,
            "url": url
        })
    except DDLException as e:
        logger.error(f"SharerPW error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SharerPW extraction failed: {str(e)}"
        )
    except Exception as e:
        logger.exception(f"Unexpected SharerPW error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}"
        )

@router.get("/sharer")
async def sharer_endpoint(url: str = Query(..., description="Sharer URL")):
    """Extract download links from Sharer platforms"""
    try:
        result = await sharer_scraper_internal(url)
        return JSONResponse({
            "success": True,
            "source": "Sharer",
            "data": result,
            "url": url
        })
    except DDLException as e:
        logger.error(f"Sharer error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sharer extraction failed: {str(e)}"
        )
    except Exception as e:
        logger.exception(f"Unexpected Sharer error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}"
        )
