from fastapi import APIRouter, Query, HTTPException
from requests import get

router = APIRouter()

def bypass(url: str) -> str:
    try:
        response = get(
            f"https://iwoozie.baby/api/free/bypass?url={url}".lower().replace(" ", ""),
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/85.0.4183.121 Safari/537.36",
                "Connection": "keep-alive",
                "Referer": "https://thebypasser.com/",
                "Origin": "https://thebypasser.com",
                "Accept": "*/*",
                "Host": "iwoozie.baby",
            },
        ).json()

        if not response.get("result") or response.get("success") is not True:
            raise ValueError("Failed to bypass link")
        return response["result"]

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/linkvertise")
def bypass_endpoint(url: str = Query(..., description="The URL to bypass")):
    """
    Bypasses a given protected/shortened URL using the iwoozie.baby API.
    """
    result = bypass(url)
    return {"success": True, "bypassed_url": result}
