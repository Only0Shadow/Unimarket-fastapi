import cloudinary_config
"""
Application entrypoint. Wires together configuration, database, static
files, templates, and every feature router. Kept intentionally thin --
business logic lives in each module's service.py, not here.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Base, engine, get_db
from app.dependencies import get_current_user

# Import every model module so SQLAlchemy's metadata knows about all tables
# before create_all() runs (relationships are resolved by class-name string,
# so this import is required even though nothing here uses the names).
from app.auth import models as auth_models  # noqa: F401
from app.users import models as users_models  # noqa: F401
from app.vendors import models as vendors_models  # noqa: F401
from app.categories import models as categories_models  # noqa: F401
from app.products import models as products_models  # noqa: F401
from app.carts import models as carts_models  # noqa: F401
from app.wishlists import models as wishlists_models  # noqa: F401
from app.orders import models as orders_models  # noqa: F401
from app.reviews import models as reviews_models  # noqa: F401
from app.notifications import models as notifications_models  # noqa: F401
from app.payments import models as payments_models  # noqa: F401

from app.auth.routes import router as auth_router
from app.users.routes import router as users_router
from app.vendors.routes import router as vendors_router
from app.categories.routes import router as categories_router
from app.products.routes import router as products_router
from app.carts.routes import router as carts_router
from app.wishlists.routes import router as wishlists_router
from app.orders.routes import router as orders_router
from app.reviews.routes import router as reviews_router
from app.notifications.routes import router as notifications_router
from app.payments.routes import router as payments_router
from app.admin.routes import router as admin_router

from app.products import service as products_service
from app.vendors import service as vendors_service
from app.categories import service as categories_service
from app.notifications import service as notifications_service

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables if they don't exist yet. Alembic migrations (see
    migrations/) are the source of truth for schema evolution beyond the
    initial create_all convenience for local development."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(vendors_router)
app.include_router(categories_router)
app.include_router(products_router)
app.include_router(carts_router)
app.include_router(wishlists_router)
app.include_router(orders_router)
app.include_router(reviews_router)
app.include_router(notifications_router)
app.include_router(payments_router)
app.include_router(admin_router)


@app.get("/", response_class=HTMLResponse)
def homepage(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    context = {
        "user": user,
        "categories": categories_service.list_active_categories(db)[:8],
        "featured_products": products_service.featured_products(db),
        "latest_products": products_service.latest_products(db),
        "deals_products": products_service.deals_products(db),
        "vendors": vendors_service.list_approved_vendors(db)[:6],
    }
    return templates.TemplateResponse(request, "home.html", context)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    user = None
    try:
        db_gen = get_db()
        db = next(db_gen)
        user = get_current_user(request, db)
    except Exception:
        pass
    return templates.TemplateResponse(request, "errors/404.html", {"user": user}, status_code=404)


@app.exception_handler(403)
async def forbidden_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse(
        request, "errors/403.html", {"user": None, "detail": exc.detail}, status_code=403
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return templates.TemplateResponse(request, "errors/500.html", {"user": None}, status_code=500)
