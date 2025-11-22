import os
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response


@app.get("/api/books")
def get_books(query: str = Query(..., min_length=1, description="Search query for books")):
    """
    Fetch top 5 books for a query using Google Books API (fallback to Open Library on failure).
    Returns concise fields for UI rendering.
    """
    results = []

    # Try Google Books first
    try:
        g_url = "https://www.googleapis.com/books/v1/volumes"
        g_params = {"q": query, "maxResults": 5}
        g_res = requests.get(g_url, params=g_params, timeout=10)
        if g_res.ok:
            data = g_res.json()
            items = data.get("items", [])
            for it in items[:5]:
                vi = it.get("volumeInfo", {})
                results.append({
                    "id": it.get("id"),
                    "title": vi.get("title"),
                    "authors": vi.get("authors", []),
                    "publishedDate": vi.get("publishedDate"),
                    "description": vi.get("description"),
                    "thumbnail": (vi.get("imageLinks", {}) or {}).get("thumbnail"),
                    "infoLink": vi.get("infoLink"),
                    "averageRating": vi.get("averageRating"),
                    "ratingsCount": vi.get("ratingsCount"),
                })
    except Exception:
        pass

    # Fallback to Open Library if needed
    if not results:
        try:
            o_url = "https://openlibrary.org/search.json"
            o_params = {"q": query, "limit": 5}
            o_res = requests.get(o_url, params=o_params, timeout=10)
            if o_res.ok:
                data = o_res.json()
                docs = data.get("docs", [])
                for d in docs[:5]:
                    cover_id = d.get("cover_i")
                    thumbnail = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else None
                    results.append({
                        "id": d.get("key"),
                        "title": d.get("title"),
                        "authors": d.get("author_name", []),
                        "publishedDate": str(d.get("first_publish_year", "")),
                        "description": None,
                        "thumbnail": thumbnail,
                        "infoLink": f"https://openlibrary.org{d.get('key')}" if d.get('key') else None,
                        "averageRating": None,
                        "ratingsCount": None,
                    })
        except Exception:
            pass

    return {"query": query, "count": len(results), "results": results}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
