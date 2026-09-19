"""Vendor-facing routes: apply to sell, manage store, dashboard, own products."""
from fastapi import APIRouter, Depends, Request, Form, status, Query
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_user, require_vendor, get_current_user
from app.vendors.schemas import VendorApplyIn, VendorUpdateIn
from app.vendors import service as vendors_service
from app.products import service as products_service
from app.categories import service as categories_service
from app.products.schemas import ProductIn

router = APIRouter(tags=["vendors"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/stores", response_class=HTMLResponse)
def list_stores(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    vendors = vendors_service.list_approved_vendors(db)
    return templates.TemplateResponse(request, "vendor/store_list.html", {"vendors": vendors, "user": user})


@router.get("/stores/{slug}", response_class=HTMLResponse)
def store_detail(
    slug: str, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user),
    page: int = Query(1, ge=1),
):
    vendor = vendors_service.get_vendor_by_slug(db, slug)
    if vendor is None:
        return templates.TemplateResponse(request, "errors/404.html", {"user": user}, status_code=404)
    result = products_service.search_products(db, vendor_id=vendor.id, page=page)
    return templates.TemplateResponse(
        request, "vendor/store_detail.html", {"vendor": vendor, "page_obj": result, "user": user}
    )


@router.get("/vendor/apply", response_class=HTMLResponse)
def apply_form(request: Request, user=Depends(require_user)):
    return templates.TemplateResponse(request, "vendor/apply.html", {"user": user, "error": None})


@router.post("/vendor/apply")
def apply_submit(
    request: Request,
    user=Depends(require_user),
    db: Session = Depends(get_db),
    store_name: str = Form(...),
    description: str = Form(""),
    contact_email: str = Form(""),
    contact_phone: str = Form(""),
):
    try:
        data = VendorApplyIn(
            store_name=store_name,
            description=description or None,
            contact_email=contact_email or None,
            contact_phone=contact_phone or None,
        )
        vendors_service.apply_as_vendor(db, user, data)
    except vendors_service.VendorError as exc:
        return templates.TemplateResponse(
            request, "vendor/apply.html", {"user": user, "error": str(exc)}, status_code=400
        )
    return RedirectResponse("/account", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/vendor/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, user=Depends(require_vendor), db: Session = Depends(get_db)):
    stats = vendors_service.dashboard_stats(db, user.vendor)
    products = products_service.list_vendor_products(db, user.vendor.id)
    return templates.TemplateResponse(
        request, "vendor/dashboard.html", {"user": user, "vendor": user.vendor, "stats": stats, "products": products}
    )


@router.get("/vendor/store/edit", response_class=HTMLResponse)
def edit_store_form(request: Request, user=Depends(require_vendor)):
    return templates.TemplateResponse(request, "vendor/edit_store.html", {"user": user, "vendor": user.vendor})


@router.post("/vendor/store/edit")
def edit_store_submit(
    request: Request,
    user=Depends(require_vendor),
    db: Session = Depends(get_db),
    store_name: str = Form(...),
    description: str = Form(""),
    logo: str = Form(""),
    banner: str = Form(""),
    contact_email: str = Form(""),
    contact_phone: str = Form(""),
):
    data = VendorUpdateIn(
        store_name=store_name,
        description=description or None,
        logo=logo or None,
        banner=banner or None,
        contact_email=contact_email or None,
        contact_phone=contact_phone or None,
    )
    vendors_service.update_store(db, user.vendor, data)
    return RedirectResponse("/vendor/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/vendor/products/new", response_class=HTMLResponse)
def new_product_form(request: Request, user=Depends(require_vendor), db: Session = Depends(get_db)):
    categories = categories_service.list_active_categories(db)
    return templates.TemplateResponse(
        request, "vendor/product_form.html", {"user": user, "categories": categories, "product": None, "error": None}
    )


@router.post("/vendor/products/new")
def create_product_submit(
    request: Request,
    user=Depends(require_vendor),
    db: Session = Depends(get_db),
    name: str = Form(...),
    short_description: str = Form(""),
    description: str = Form(""),
    category_id: int = Form(...),
    price: float = Form(...),
    previous_price: str = Form(""),
    quantity_available: int = Form(...),
    brand: str = Form(""),
    condition: str = Form("new"),
    image: str = Form(""),
    is_featured: bool = Form(False),
):
    try:
        data = ProductIn(
            name=name,
            short_description=short_description or None,
            description=description or None,
            category_id=category_id,
            price=price,
            previous_price=float(previous_price) if previous_price else None,
            quantity_available=quantity_available,
            brand=brand or None,
            condition=condition,
            image=image or None,
            is_featured=is_featured,
        )
        products_service.create_product(db, user.vendor, data)
    except (products_service.ProductError, ValueError) as exc:
        categories = categories_service.list_active_categories(db)
        return templates.TemplateResponse(
            request,
            "vendor/product_form.html",
            {"user": user, "categories": categories, "product": None, "error": str(exc)},
            status_code=400,
        )
    return RedirectResponse("/vendor/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/vendor/products/{product_id}/edit", response_class=HTMLResponse)
def edit_product_form(
    product_id: int, request: Request, user=Depends(require_vendor), db: Session = Depends(get_db)
):
    product = products_service.get_product_owned(db, product_id, user.vendor.id)
    if product is None:
        return templates.TemplateResponse(request, "errors/404.html", {"user": user}, status_code=404)
    categories = categories_service.list_active_categories(db)
    return templates.TemplateResponse(
        request, "vendor/product_form.html", {"user": user, "categories": categories, "product": product, "error": None}
    )


@router.post("/vendor/products/{product_id}/edit")
def edit_product_submit(
    product_id: int,
    request: Request,
    user=Depends(require_vendor),
    db: Session = Depends(get_db),
    name: str = Form(...),
    short_description: str = Form(""),
    description: str = Form(""),
    category_id: int = Form(...),
    price: float = Form(...),
    previous_price: str = Form(""),
    quantity_available: int = Form(...),
    brand: str = Form(""),
    condition: str = Form("new"),
    image: str = Form(""),
    is_featured: bool = Form(False),
    is_active: bool = Form(True),
):
    product = products_service.get_product_owned(db, product_id, user.vendor.id)
    if product is None:
        return templates.TemplateResponse(request, "errors/404.html", {"user": user}, status_code=404)
    try:
        data = ProductIn(
            name=name,
            short_description=short_description or None,
            description=description or None,
            category_id=category_id,
            price=price,
            previous_price=float(previous_price) if previous_price else None,
            quantity_available=quantity_available,
            brand=brand or None,
            condition=condition,
            image=image or None,
            is_featured=is_featured,
            is_active=is_active,
        )
        products_service.update_product(db, product, data)
    except (products_service.ProductError, ValueError) as exc:
        categories = categories_service.list_active_categories(db)
        return templates.TemplateResponse(
            request,
            "vendor/product_form.html",
            {"user": user, "categories": categories, "product": product, "error": str(exc)},
            status_code=400,
        )
    return RedirectResponse("/vendor/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/vendor/products/{product_id}/archive")
def archive_product(product_id: int, user=Depends(require_vendor), db: Session = Depends(get_db)):
    product = products_service.get_product_owned(db, product_id, user.vendor.id)
    if product is not None:
        products_service.archive_product(db, product)
    return RedirectResponse("/vendor/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/vendor/orders", response_class=HTMLResponse)
def vendor_orders(request: Request, user=Depends(require_vendor), db: Session = Depends(get_db)):
    from app.orders import service as orders_service
    orders = orders_service.list_orders_containing_vendor(db, user.vendor.id)
    return templates.TemplateResponse(request, "vendor/orders.html", {"user": user, "orders": orders})
