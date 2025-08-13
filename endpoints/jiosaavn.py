"""
JioSaavn music API endpoint
"""
import time
import logging
import asyncio
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel, Field
import aiohttp

logger = logging.getLogger(__name__)
router = APIRouter()

# JioSaavn API Base URL
JIOSAAVN_BASE_URL = "https://jiosavanwave.vercel.app/api"

class JioSaavnResponse(BaseModel):
    """Base response model for JioSaavn API"""
    success: bool = Field(..., description="Request success status")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    message: Optional[str] = Field(None, description="Error message if any")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")

class JioSaavnSearchRequest(BaseModel):
    """Request model for JioSaavn search"""
    query: str = Field(..., min_length=1, max_length=200, description="Search query")
    page: int = Field(0, ge=0, le=100, description="Page number")
    limit: int = Field(10, ge=1, le=50, description="Results per page")

async def make_jiosaavn_request(endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Make request to JioSaavn API with error handling"""
    url = f"{JIOSAAVN_BASE_URL}/{endpoint.lstrip('/')}"
    
    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(url, params=params or {}) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"JioSaavn API returned status {response.status}"
                    )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail="JioSaavn API request timed out"
            )
        except aiohttp.ClientError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"JioSaavn API connection error: {str(e)}"
            )

@router.get("/jiosaavn/search", response_model=JioSaavnResponse)
async def jiosaavn_global_search(
    query: str = Query(..., min_length=1, max_length=200, description="Search query"),
):
    """Global search across songs, albums, artists, and playlists"""
    start_time = time.time()
    
    try:
        logger.info(f"JioSaavn global search: {query}")
        
        result = await make_jiosaavn_request("search", {"query": query})
        processing_time = time.time() - start_time
        
        return JioSaavnResponse(
            success=True,
            data=result.get("data", {}),
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"JioSaavn global search error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(exc)}"
        )

@router.get("/jiosaavn/search/songs", response_model=JioSaavnResponse)
async def jiosaavn_search_songs(
    query: str = Query(..., min_length=1, max_length=200, description="Search query for songs"),
    page: int = Query(0, ge=0, le=100, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Results per page")
):
    """Search for songs specifically"""
    start_time = time.time()
    
    try:
        logger.info(f"JioSaavn song search: {query} (page={page}, limit={limit})")
        
        params = {
            "query": query,
            "page": page,
            "limit": limit
        }
        
        result = await make_jiosaavn_request("search/songs", params)
        processing_time = time.time() - start_time
        
        return JioSaavnResponse(
            success=True,
            data=result.get("data", {}),
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"JioSaavn song search error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Song search failed: {str(exc)}"
        )

@router.get("/jiosaavn/search/albums", response_model=JioSaavnResponse)
async def jiosaavn_search_albums(
    query: str = Query(..., min_length=1, max_length=200, description="Search query for albums"),
    page: int = Query(0, ge=0, le=100, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Results per page")
):
    """Search for albums specifically"""
    start_time = time.time()
    
    try:
        logger.info(f"JioSaavn album search: {query} (page={page}, limit={limit})")
        
        params = {
            "query": query,
            "page": page,
            "limit": limit
        }
        
        result = await make_jiosaavn_request("search/albums", params)
        processing_time = time.time() - start_time
        
        return JioSaavnResponse(
            success=True,
            data=result.get("data", {}),
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"JioSaavn album search error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Album search failed: {str(exc)}"
        )

@router.get("/jiosaavn/search/artists", response_model=JioSaavnResponse)
async def jiosaavn_search_artists(
    query: str = Query(..., min_length=1, max_length=200, description="Search query for artists"),
    page: int = Query(0, ge=0, le=100, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Results per page")
):
    """Search for artists specifically"""
    start_time = time.time()
    
    try:
        logger.info(f"JioSaavn artist search: {query} (page={page}, limit={limit})")
        
        params = {
            "query": query,
            "page": page,
            "limit": limit
        }
        
        result = await make_jiosaavn_request("search/artists", params)
        processing_time = time.time() - start_time
        
        return JioSaavnResponse(
            success=True,
            data=result.get("data", {}),
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"JioSaavn artist search error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Artist search failed: {str(exc)}"
        )

@router.get("/jiosaavn/search/playlists", response_model=JioSaavnResponse)
async def jiosaavn_search_playlists(
    query: str = Query(..., min_length=1, max_length=200, description="Search query for playlists"),
    page: int = Query(0, ge=0, le=100, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Results per page")
):
    """Search for playlists specifically"""
    start_time = time.time()
    
    try:
        logger.info(f"JioSaavn playlist search: {query} (page={page}, limit={limit})")
        
        params = {
            "query": query,
            "page": page,
            "limit": limit
        }
        
        result = await make_jiosaavn_request("search/playlists", params)
        processing_time = time.time() - start_time
        
        return JioSaavnResponse(
            success=True,
            data=result.get("data", {}),
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"JioSaavn playlist search error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Playlist search failed: {str(exc)}"
        )

@router.get("/jiosaavn/songs", response_model=JioSaavnResponse)
async def jiosaavn_get_songs(
    ids: Optional[str] = Query(None, description="Comma-separated song IDs"),
    link: Optional[str] = Query(None, description="Direct JioSaavn song link")
):
    """Get songs by IDs or link"""
    start_time = time.time()
    
    if not ids and not link:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'ids' or 'link' parameter is required"
        )
    
    try:
        params = {}
        if ids:
            params["ids"] = ids
        if link:
            params["link"] = link
            
        logger.info(f"JioSaavn get songs: {params}")
        
        result = await make_jiosaavn_request("songs", params)
        processing_time = time.time() - start_time
        
        return JioSaavnResponse(
            success=True,
            data=result.get("data", {}),
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"JioSaavn get songs error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Get songs failed: {str(exc)}"
        )

@router.get("/jiosaavn/songs/{song_id}", response_model=JioSaavnResponse)
async def get_song(song_id: str):
    """Get song by ID"""
    start_time = time.time()
    
    try:
        logger.info(f"JioSaavn get song by ID: {song_id}")
        
        result = await make_jiosaavn_request(f"songs/{song_id}")
        processing_time = time.time() - start_time
        
        return JioSaavnResponse(
            success=True,
            data=result.get("data", {}),
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"JioSaavn get song by ID error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Get song by ID failed: {str(exc)}"
        )

@router.get("/jiosaavn/songs/{song_id}/suggestions", response_model=JioSaavnResponse)
async def jiosaavn_get_song_suggestions(
    song_id: str = Query(..., description="Song ID"),
    limit: int = Query(10, ge=1, le=50, description="Number of suggestions")
):
    """Get song suggestions"""
    start_time = time.time()
    
    try:
        logger.info(f"JioSaavn get song suggestions: {song_id} (limit={limit})")
        
        params = {"limit": limit}
        result = await make_jiosaavn_request(f"songs/{song_id}/suggestions", params)
        processing_time = time.time() - start_time
        
        return JioSaavnResponse(
            success=True,
            data=result.get("data", {}),
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"JioSaavn get song suggestions error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Get song suggestions failed: {str(exc)}"
        )

@router.get("/jiosaavn/albums", response_model=JioSaavnResponse)
async def jiosaavn_get_album(
    id: Optional[str] = Query(None, description="Album ID"),
    link: Optional[str] = Query(None, description="Direct JioSaavn album link")
):
    """Get album by ID or link"""
    start_time = time.time()
    
    if not id and not link:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'id' or 'link' parameter is required"
        )
    
    try:
        params = {}
        if id:
            params["id"] = id
        if link:
            params["link"] = link
            
        logger.info(f"JioSaavn get album: {params}")
        
        result = await make_jiosaavn_request("albums", params)
        processing_time = time.time() - start_time
        
        return JioSaavnResponse(
            success=True,
            data=result.get("data", {}),
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"JioSaavn get album error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Get album failed: {str(exc)}"
        )

@router.get("/jiosaavn/artists", response_model=JioSaavnResponse)
async def jiosaavn_get_artist(
    id: Optional[str] = Query(None, description="Artist ID"),
    link: Optional[str] = Query(None, description="Direct JioSaavn artist link"),
    page: int = Query(0, ge=0, description="Page number"),
    song_count: int = Query(10, ge=1, le=50, description="Number of songs"),
    album_count: int = Query(10, ge=1, le=50, description="Number of albums"),
    sort_by: str = Query("popularity", description="Sort by"),
    sort_order: str = Query("desc", description="Sort order")
):
    """Get artist by ID or link"""
    start_time = time.time()
    
    if not id and not link:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'id' or 'link' parameter is required"
        )
    
    try:
        params = {
            "page": page,
            "songCount": song_count,
            "albumCount": album_count,
            "sortBy": sort_by,
            "sortOrder": sort_order
        }
        
        if id:
            params["id"] = id
        if link:
            params["link"] = link
            
        logger.info(f"JioSaavn get artist: {params}")
        
        result = await make_jiosaavn_request("artists", params)
        processing_time = time.time() - start_time
        
        return JioSaavnResponse(
            success=True,
            data=result.get("data", {}),
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"JioSaavn get artist error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Get artist failed: {str(exc)}"
        )

@router.get("/jiosaavn/artists/{artist_id}", response_model=JioSaavnResponse)
async def jiosaavn_get_artist_by_id(
    artist_id: str = Query(..., description="Artist ID"),
    page: int = Query(0, ge=0, description="Page number"),
    song_count: int = Query(10, ge=1, le=50, description="Number of songs"),
    album_count: int = Query(10, ge=1, le=50, description="Number of albums"),
    sort_by: str = Query("popularity", description="Sort by"),
    sort_order: str = Query("desc", description="Sort order")
):
    """Get artist by ID"""
    start_time = time.time()
    
    try:
        params = {
            "page": page,
            "songCount": song_count,
            "albumCount": album_count,
            "sortBy": sort_by,
            "sortOrder": sort_order
        }
        
        logger.info(f"JioSaavn get artist by ID: {artist_id}")
        
        result = await make_jiosaavn_request(f"artists/{artist_id}", params)
        processing_time = time.time() - start_time
        
        return JioSaavnResponse(
            success=True,
            data=result.get("data", {}),
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"JioSaavn get artist by ID error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Get artist by ID failed: {str(exc)}"
        )

@router.get("/jiosaavn/artists/{artist_id}/songs", response_model=JioSaavnResponse)
async def jiosaavn_get_artist_songs(
    artist_id: str = Query(..., description="Artist ID"),
    page: int = Query(0, ge=0, description="Page number"),
    sort_by: str = Query("popularity", description="Sort by"),
    sort_order: str = Query("desc", description="Sort order")
):
    """Get artist's songs"""
    start_time = time.time()
    
    try:
        params = {
            "page": page,
            "sortBy": sort_by,
            "sortOrder": sort_order
        }
        
        logger.info(f"JioSaavn get artist songs: {artist_id}")
        
        result = await make_jiosaavn_request(f"artists/{artist_id}/songs", params)
        processing_time = time.time() - start_time
        
        return JioSaavnResponse(
            success=True,
            data=result.get("data", {}),
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"JioSaavn get artist songs error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Get artist songs failed: {str(exc)}"
        )

@router.get("/jiosaavn/artists/{artist_id}/albums", response_model=JioSaavnResponse)
async def jiosaavn_get_artist_albums(
    artist_id: str = Query(..., description="Artist ID"),
    page: int = Query(0, ge=0, description="Page number"),
    sort_by: str = Query("popularity", description="Sort by"),
    sort_order: str = Query("desc", description="Sort order")
):
    """Get artist's albums"""
    start_time = time.time()
    
    try:
        params = {
            "page": page,
            "sortBy": sort_by,
            "sortOrder": sort_order
        }
        
        logger.info(f"JioSaavn get artist albums: {artist_id}")
        
        result = await make_jiosaavn_request(f"artists/{artist_id}/albums", params)
        processing_time = time.time() - start_time
        
        return JioSaavnResponse(
            success=True,
            data=result.get("data", {}),
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"JioSaavn get artist albums error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Get artist albums failed: {str(exc)}"
        )

@router.get("/jiosaavn/playlists", response_model=JioSaavnResponse)
async def jiosaavn_get_playlist(
    id: Optional[str] = Query(None, description="Playlist ID"),
    link: Optional[str] = Query(None, description="Direct JioSaavn playlist link"),
    page: int = Query(0, ge=0, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Songs per page")
):
    """Get playlist by ID or link"""
    start_time = time.time()
    
    if not id and not link:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'id' or 'link' parameter is required"
        )
    
    try:
        params = {
            "page": page,
            "limit": limit
        }
        
        if id:
            params["id"] = id
        if link:
            params["link"] = link
            
        logger.info(f"JioSaavn get playlist: {params}")
        
        result = await make_jiosaavn_request("playlists", params)
        processing_time = time.time() - start_time
        
        return JioSaavnResponse(
            success=True,
            data=result.get("data", {}),
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"JioSaavn get playlist error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Get playlist failed: {str(exc)}"
        )
