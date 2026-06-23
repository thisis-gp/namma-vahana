"""Local / non-Vercel FastAPI entry."""
from backend.app_factory import create_app

app = create_app("/api")


def main() -> None:
    import uvicorn

    from backend.config import HOST, PORT

    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=False)


if __name__ == "__main__":
    main()
