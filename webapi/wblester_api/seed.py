"""Seed the MongoDB database with baseline CMS content.

Run inside the api container:  python -m wblester_api.seed
Idempotent: existing records are left untouched.

The seeded content forms a complete public website for "WBLester & O":
categories are menus, pages are submenus, and pages may carry subpages
(parent_id) which render as nested submenu items. Block types rendered by
the single-page web front end: jumbotron, about, cards, features, steps,
stats, gallery, testimonials, partners, richText, cta, contactForm.
"""

import os
import shutil

from .models import (
    Categories,
    Files,
    Images,
    MailTemplates,
    Pages,
    Permissions,
    RolePermissions,
    Roles,
    SiteSettings,
    Users,
)
from .utils.helpers import next_id

# Overridable at runtime (see __main__); falls back to env/config defaults.
RUNTIME_CONFIG = {}

ROLES = [
    (0, "superuser", "Unrestricted access"),
    (1, "admin", "Full admin panel access"),
    (2, "guest", "Read-only access to published data"),
]

PERMISSIONS = [
    ("pages", "Manage website pages"),
    ("categories", "Manage page categories"),
    ("settings", "Change site settings"),
    ("users", "Manage user accounts"),
    ("roles", "Manage roles and permission matrix"),
    ("permissions", "View and extend permission registry"),
    ("messages", "Operate the contact mailbox"),
    ("files", "Upload images and files"),
    ("audit_trail", "Inspect the audit trail"),
]

# access levels: 0 read-only, 1 read+modify, 2 create/delete
MATRIX = {
    0: {p[0]: 2 for p in PERMISSIONS},                      # superuser (implicit)
    1: {p[0]: 2 for p in PERMISSIONS},                      # admin: full panel access
    2: {p[0]: 0 for p in PERMISSIONS},                      # guest
}

CATEGORIES = [
    (1, None, "Agriculture", "agriculture", 1),
    (2, None, "Real Estate", "real-estate", 2),
    (3, None, "Natural Resources & Energy", "natural-resources-energy", 3),
]

SEED_DIR = os.path.join(os.path.dirname(__file__), "seed_assets")

MEDIA = [
    # (file_name, alt title used for the Images document)
    ("agriculture-hero.jpg", "Golden wheat field at harvest"),
    ("crops.jpg", "Tractor ploughing a farm field"),
    ("livestock.jpg", "Cattle grazing on open pasture"),
    ("realestate-hero.jpg", "Modern residential property at dusk"),
    ("listings.jpg", "Residential neighbourhood street"),
    ("valuations.jpg", "City skyline of commercial buildings"),
    ("energy-hero.jpg", "Solar panels and wind turbines"),
    ("mining.jpg", "Open-pit mining operations"),
    ("garden-design.jpg", "Formal English garden with manicured flower beds"),
    ("lawn-care.jpg", "Professional mower finishing a lush striped lawn"),
    ("landscaping.jpg", "Sunken parterre garden with crisp hedging"),
    ("hedge-topiary.jpg", "Specialist trimming sculpted hedges and topiary"),
    ("greenhouse.jpg", "Greenhouse nursery with thriving young plants"),
    ("orchard.jpg", "Apple orchard rows in spring grass"),
    ("tree-planting.jpg", "Hands planting a young sapling in rich soil"),
    ("green-hills.jpg", "Rolling green hills of managed farmland"),
    ("garden-estate.jpg", "Country residence framed by pond and lawns"),
    ("nature-reserve.jpg", "Waterfall rushing through lush green forest"),
    ("irrigation-pivot.jpg", "Aerial view of a centre-pivot irrigation system"),
    ("interior.jpg", "Modern living room interior of a listed residence"),
    ("solar-install.jpg", "Technician installing photovoltaic solar panels"),
    ("wind-farm.jpg", "Wind turbines on rolling farmland"),
    ("feedlot.jpg", "Herd of beef cattle on open pasture"),
]

# page_id, category_id, parent_id, slug, title, sort_order, hero_image
PAGES = [
    # Company landing (drives the home route; hidden from menus)
    (100, None, None, "home", "WBLester & O", 0, "energy-hero.jpg"),

    # Agriculture --------------------------------------------------------
    (101, 1, None, "agriculture-home", "Agriculture", 1, "agriculture-hero.jpg"),
    (102, 1, None, "crop-farming-advisory", "Crop Farming & Advisory", 2, "crops.jpg"),
    (104, 1, 102, "soil-analysis", "Soil Analysis & Land Preparation", 3, "crops.jpg"),
    (105, 1, 102, "irrigation-systems", "Irrigation Systems", 4, "crops.jpg"),
    (103, 1, None, "livestock-poultry", "Livestock & Poultry", 5, "livestock.jpg"),
    (106, 1, 103, "veterinary-support", "Veterinary Support Services", 6, "livestock.jpg"),

    # Real Estate ----------------------------------------------------------
    (201, 2, None, "real-estate-home", "Real Estate", 1, "realestate-hero.jpg"),
    (202, 2, None, "property-listings", "Property Listings", 2, "listings.jpg"),
    (204, 2, 202, "residential-sales", "Residential Sales", 3, "listings.jpg"),
    (205, 2, 202, "commercial-leasing", "Commercial Leasing", 4, "valuations.jpg"),
    (203, 2, None, "valuations-consultancy", "Valuations & Consultancy", 5, "valuations.jpg"),
    (206, 2, 203, "investment-advisory", "Investment Advisory", 6, "valuations.jpg"),

    # Natural Resources & Energy -------------------------------------------
    (301, 3, None, "energy-home", "Natural Resources & Energy", 1, "energy-hero.jpg"),
    (302, 3, None, "mining-minerals", "Mining & Minerals", 2, "mining.jpg"),
    (304, 3, 302, "mineral-exploration", "Mineral Exploration & Licensing", 3, "mining.jpg"),
    (303, 3, None, "renewable-energy", "Renewable Energy Projects", 4, "energy-hero.jpg"),
    (305, 3, 303, "solar-solutions", "Solar Solutions", 5, "energy-hero.jpg"),
    (306, 3, 303, "wind-farms", "Wind Farm Development", 6, "energy-hero.jpg"),
]


def media_url(file_name: str) -> str:
    base = RUNTIME_CONFIG.get(
        "PUBLIC_BASE_URL",
        os.environ.get(
            "PUBLIC_BASE_URL", f"http://localhost:{os.environ.get('PORT', '5454')}"
        ),
    )
    return f"{base}/uploads/{file_name}"


def seed() -> None:
    _seed_roles()
    _seed_permissions()
    _seed_matrix()
    _seed_superuser()
    _seed_default_admin()
    _seed_settings()
    _seed_categories()
    _seed_media()
    _seed_pages()
    _seed_mail_templates()
    print("Seed complete.")


def _seed_roles() -> None:
    for role_id, name, description in ROLES:
        if Roles.objects(role_id=role_id).first():
            continue
        Roles(role_id=role_id, role_name=name, description=description).save()


def _seed_permissions() -> None:
    for name, description in PERMISSIONS:
        if Permissions.objects(permission_name=name).first():
            continue
        Permissions(permission_id=next_id(Permissions, "permission_id"), permission_name=name, description=description).save()


def _seed_matrix() -> None:
    perm_by_name = {p.permission_name: p.permission_id for p in Permissions.objects()}
    for role_id, grants in MATRIX.items():
        if role_id == 0:
            continue  # superuser bypasses the matrix entirely
        for perm_name, level in grants.items():
            pid = perm_by_name.get(perm_name)
            if pid is None:
                continue
            grant = RolePermissions.objects(role_id=role_id, permission_id=pid).first()
            if grant is None:
                RolePermissions(role_id=role_id, permission_id=pid, access_level=level).save()
            elif role_id == 1 and grant.access_level != level:
                # Keep the default admin role at full grants even after upgrades.
                grant.access_level = level
                grant.save()


def _seed_superuser() -> None:
    username = os.environ.get("WBLESTER_ADMIN_USERNAME", "wblester")
    password = os.environ.get("WBLESTER_ADMIN_PASSWORD", "WBLester@123")
    email = os.environ.get("WBLESTER_ADMIN_EMAIL", "admin@wblester.local")

    if Users.objects(username=username).first():
        return
    user = Users(
        user_id=next_id(Users, "user_id"),
        username=username,
        email=email,
        role_id=0,
        active=True,
        status=Users.ACTIVE,
    )
    user.set_password(password)
    user.password_history = [user.password_hash]
    user.save()
    print(f"Superuser '{username}' created with configured password.")


def _seed_default_admin() -> None:
    username = os.environ.get("WBLESTER_DEFAULT_ADMIN_USERNAME", "wblesteradmin")
    password = os.environ.get("WBLESTER_DEFAULT_ADMIN_PASSWORD", "WbLester@123!")
    email = os.environ.get("WBLESTER_DEFAULT_ADMIN_EMAIL", "wblesteradmin@wblester.local")

    if Users.objects(username=username).first():
        return
    user = Users(
        user_id=next_id(Users, "user_id"),
        username=username,
        email=email,
        role_id=1,
        active=True,
        status=Users.ACTIVE,
    )
    user.set_password(password)
    user.password_history = [user.password_hash]
    user.save()
    print(f"Default admin '{username}' created with configured password.")


def _seed_settings() -> None:
    if SiteSettings.objects().first():
        return
    SiteSettings(
        settings_id=1,
        site_name="WBLester & O",
        site_title="WBLester & O",
        site_logo="/assets/logo.svg",
        site_description=(
            "Agriculture, Real Estate, and Natural Resources & Energy — "
            "one trusted partner from soil to skyline."
        ),
        email=os.environ.get("WBLESTER_ADMIN_EMAIL", "info@wblester.local"),
        phone_number="+263 772 000 000",
        address="12 Harvest House, Independence Avenue, Harare",
        mailing_list=[os.environ.get("WBLESTER_ADMIN_EMAIL", "admin@wblester.local")],
        contact_us_message=(
            "Tell us about your project and our team will respond within one "
            "business day."
        ),
        google_map=(
            "https://www.openstreetmap.org/export/embed.html"
            "?bbox=30.99%2C-17.83%2C31.06%2C-17.78&layer=mapnik"
        ),
        home_page_id=100,
        sync_mode=SiteSettings.ONLINE,
    ).save()


def _seed_categories() -> None:
    for category_id, parent_id, name, slug, sort_order in CATEGORIES:
        if Categories.objects(category_id=category_id).first():
            continue
        Categories(
            category_id=category_id,
            parent_id=parent_id,
            category_name=name,
            slug=slug,
            visible=True,
            sort_order=sort_order,
        ).save()


def _seed_media() -> None:
    """Copy bundled photos into UPLOAD_DIR and register them as Images."""
    upload_dir = RUNTIME_CONFIG.get(
        "UPLOAD_DIR",
        os.environ.get("UPLOAD_DIR", "/srv/api/uploads"),
    )
    os.makedirs(upload_dir, exist_ok=True)
    for file_name, title in MEDIA:
        src = os.path.join(SEED_DIR, file_name)
        dest = os.path.join(upload_dir, file_name)
        if not os.path.exists(src):
            print(f"Seed asset missing, skipped: {src}")
            continue
        if not os.path.exists(dest):
            shutil.copyfile(src, dest)
        if Images.objects(file_name=file_name).first():
            continue
        Images(
            image_id=next_id(Images, "image_id"),
            image_name=title,
            file_name=file_name,
            file_path=dest,
            image_type="image/jpeg",
            file_size=str(os.path.getsize(dest)),
            image_format="jpg",
            file_type="image/jpeg",
            image_url=f"/uploads/{file_name}",
        ).save()


def _blocks(page_id: int) -> dict:
    """Content blocks per page id. Rendered by the Flutter block renderer."""
    img = media_url
    content = {

        # ------------------------------------------------------------------
        # HOME — fully CMS-editable marketing page
        # ------------------------------------------------------------------
        100: {
            "blocks": [
                {
                    "id": "home-jumbotron",
                    "type": "jumbotron",
                    "slides": [
                        {
                            "imageUrl": img("green-hills.jpg"),
                            "kicker": "Welcome to WBLester & O",
                            "title": "We Grow [Value] From the Ground Up",
                            "subtitle": (
                                "Agriculture, property and energy projects delivered "
                                "by one accountable team — from first soil test to "
                                "final handover."
                            ),
                            "ctaLabel": "Explore our services",
                            "ctaSlug": "agriculture-home",
                        },
                        {
                            "imageUrl": img("agriculture-hero.jpg"),
                            "kicker": "Agriculture",
                            "title": "Farming That [Pays] Its Own Way",
                            "subtitle": (
                                "Agronomy, livestock programmes and water systems "
                                "that lift yields 20–40% within two seasons."
                            ),
                            "ctaLabel": "Discover agriculture",
                            "ctaSlug": "agriculture-home",
                        },
                        {
                            "imageUrl": img("garden-estate.jpg"),
                            "kicker": "Real Estate",
                            "title": "Property, Handled [Properly]",
                            "subtitle": (
                                "Verified listings, bank-grade valuations and "
                                "negotiators who close — residential to commercial."
                            ),
                            "ctaLabel": "Discover real estate",
                            "ctaSlug": "real-estate-home",
                        },
                        {
                            "imageUrl": img("energy-hero.jpg"),
                            "kicker": "Natural Resources & Energy",
                            "title": "Powering Tomorrow, [Responsibly]",
                            "subtitle": (
                                "Utility-scale solar and wind plus compliant mining "
                                "services engineered to international ESG standards."
                            ),
                            "ctaLabel": "Discover energy",
                            "ctaSlug": "energy-home",
                        },
                        {
                            "imageUrl": img("landscaping.jpg"),
                            "kicker": "Grounds & Gardens",
                            "title": "Landscapes We Are [Proud] To Stand Behind",
                            "subtitle": (
                                "Design, build and aftercare for estates, lodges and "
                                "commercial grounds — always in bloom."
                            ),
                            "ctaLabel": "Request grounds care",
                            "ctaSlug": "contact",
                        },
                    ],
                },
                {
                    "id": "home-services",
                    "type": "cards",
                    "title": "Services built around your ambitions",
                    "intro": (
                        "Welcome to WBLester & O — three sectors delivered by one "
                        "accountable in-house team, so nothing is lost between contractors."
                    ),
                    "items": [
                        {
                            "title": "Crop & Farm Advisory",
                            "text": "Season-long agronomy, soil programmes and input sourcing that raise yields year after year.",
                            "imageUrl": img("agriculture-hero.jpg"),
                            "slug": "crop-farming-advisory",
                        },
                        {
                            "title": "Livestock & Poultry",
                            "text": "Breeding, nutrition and 24/7 veterinary cover for healthier herds and better margins.",
                            "imageUrl": img("livestock.jpg"),
                            "slug": "livestock-poultry",
                        },
                        {
                            "title": "Grounds & Gardens",
                            "text": "Estate gardens, lawns and commercial landscapes designed, built and kept immaculate.",
                            "imageUrl": img("lawn-care.jpg"),
                            "slug": "contact",
                        },
                        {
                            "title": "Property Sales & Leasing",
                            "text": "Verified homes and commercial space with transparent fees from viewing to keys.",
                            "imageUrl": img("realestate-hero.jpg"),
                            "slug": "real-estate-home",
                        },
                        {
                            "title": "Valuations & Advisory",
                            "text": "Bank-grade valuation reports accepted by major lenders across the region.",
                            "imageUrl": img("valuations.jpg"),
                            "slug": "valuations-consultancy",
                        },
                        {
                            "title": "Renewables & Mining",
                            "text": "Solar plants, wind farms and exploration services developed to global ESG practice.",
                            "imageUrl": img("energy-hero.jpg"),
                            "slug": "energy-home",
                        },
                    ],
                },
                {
                    "id": "home-features",
                    "type": "features",
                    "title": "Why clients choose WBLester & O",
                    "intro": "The guarantees behind every proposal we sign.",
                    "items": [
                        {"title": "Honest & Dependable", "text": "Fixed-fee proposals, weekly reporting and no hidden extras — ever."},
                        {"title": "25+ Years Experience", "text": "Agronomists, valuers and engineers who have delivered across the region."},
                        {"title": "Sector Specialists", "text": "Dedicated teams for agriculture, property and energy projects alike."},
                        {"title": "Award Winning Service", "text": "Recognised for sustainable land management and client care."},
                        {"title": "Licensed, Bonded & Insured", "text": "Audit-ready compliance on every engagement, large or small."},
                        {"title": "1000+ Projects Supported", "text": "From backyard gardens to utility-scale power plants."},
                    ],
                },
                {
                    "id": "home-gallery",
                    "type": "gallery",
                    "title": "Recent work across the region",
                    "intro": (
                        "A snapshot of farms, gardens, properties and energy "
                        "sites entrusted to us."
                    ),
                    "items": [
                        {"imageUrl": img("garden-design.jpg"), "caption": "Estate garden redesign", "category": "Gardens"},
                        {"imageUrl": img("lawn-care.jpg"), "caption": "Weekly grounds maintenance", "category": "Gardens"},
                        {"imageUrl": img("greenhouse.jpg"), "caption": "Nursery propagation tunnels", "category": "Farms"},
                        {"imageUrl": img("orchard.jpg"), "caption": "Orchard establishment programme", "category": "Farms"},
                        {"imageUrl": img("garden-estate.jpg"), "caption": "Country residence grounds", "category": "Estates"},
                        {"imageUrl": img("nature-reserve.jpg"), "caption": "Wetland restoration project", "category": "Estates"},
                    ],
                },
                {
                    "id": "home-about",
                    "type": "about",
                    "title": "About WBLester & O",
                    "lead": (
                        "Since our founding we have believed that land rewards "
                        "those who understand it."
                    ),
                    "body": (
                        "<p>Our agronomists, valuers, engineers and grounds teams "
                        "plan and deliver every project in-house — so nothing is "
                        "lost between contractors.</p>"
                        "<p>Whether you need 200 hectares under pivot, a bank-ready "
                        "valuation or a solar plant that performs to model, one "
                        "senior advisor owns your outcome end-to-end.</p>"
                    ),
                    "images": [img("garden-design.jpg"), img("tree-planting.jpg")],
                    "points": [
                        "Licensed, insured and audit-ready operations on every engagement",
                        "Teams on the ground executing to international standards",
                        "Transparent, itemised proposals within five working days",
                    ],
                },
                {
                    "id": "home-steps",
                    "type": "steps",
                    "title": "How we work",
                    "intro": "Simple process",
                    "items": [
                        {"title": "Consultation", "text": "A free site visit or call to understand your goals, budget and timelines."},
                        {"title": "Proposal", "text": "An itemised, fixed-fee plan with milestones — no surprises later."},
                        {"title": "Delivery", "text": "Vetted crews execute under one project manager who reports weekly."},
                        {"title": "Aftercare", "text": "We stay on contract to maintain, measure and improve results."},
                    ],
                },
                {
                    "id": "home-stats",
                    "type": "stats",
                    "backgroundImage": img("green-hills.jpg"),
                    "items": [
                        {"value": "25+", "label": "Years combined experience"},
                        {"value": "120+", "label": "Projects delivered"},
                        {"value": "40k", "label": "Hectares under management"},
                        {"value": "98%", "label": "Client retention"},
                    ],
                },
                {
                    "id": "home-testimonials",
                    "type": "testimonials",
                    "title": "What our clients say",
                    "items": [
                        {
                            "title": "Yields up by a third",
                            "quote": "Their agronomy programme lifted our maize average by a third in one season. The weekly scouting reports alone are worth the fee.",
                            "name": "R. Mhike",
                            "role": "Farm Manager, 320 ha mixed operation",
                        },
                        {
                            "title": "Eleven weeks, keys in hand",
                            "quote": "From valuation to registration in eleven weeks — and they negotiated R80k off the asking price. I would not sell or buy through anyone else.",
                            "name": "T. Banda",
                            "role": "Residential buyer",
                        },
                        {
                            "title": "Diesel bill gone in a quarter",
                            "quote": "The solar plant performs exactly to the yield model they promised. Our diesel bill disappeared in the first quarter.",
                            "name": "S. Chirwa",
                            "role": "Operations Director, agro-processing plant",
                        },
                    ],
                },
                {
                    "id": "home-partners",
                    "type": "partners",
                    "items": [
                        {"label": "AgriCorp Partners"},
                        {"label": "TerraFirm Capital"},
                        {"label": "GreenGrid Energy"},
                        {"label": "SoilScience Labs"},
                        {"label": "Estate & Country Homes"},
                        {"label": "FreshProduce Markets"},
                    ],
                },
                {
                    "id": "home-cta",
                    "type": "cta",
                    "title": "Ready to see what your land can do?",
                    "text": "Request a service today — a senior advisor responds within one business day.",
                    "buttonLabel": "Request a service",
                },
                {"id": "home-contact", "type": "contactForm"},
            ],
        },

        # ------------------------------------------------------------------
        # AGRICULTURE
        # ------------------------------------------------------------------
        101: {
            "blocks": [
                {
                    "id": "agr-hero",
                    "type": "hero",
                    "title": "Agriculture",
                    "subtitle": (
                        "Smarter farming, higher yields \u2014 agronomy, livestock and "
                        "water systems managed as a business."
                    ),
                    "imageUrl": img("agriculture-hero.jpg"),
                },
                {
                    "id": "agr-intro",
                    "type": "about",
                    "kicker": "Why partner with us",
                    "title": "Your farm, run like the enterprise it is.",
                    "body": (
                        "<p>Whether you manage five hectares or five thousand, our "
                        "agronomists and field teams work shoulder-to-shoulder with "
                        "you to plan, plant and profit. Every recommendation is "
                        "costed, measured and reported.</p>"
                    ),
                    "bullets": [
                        "20\u201340% average yield uplift within two seasons",
                        "Weekly photo-documented field reports you can audit",
                        "Input supply chains that beat retail pricing",
                    ],
                    "imageUrl": img("orchard.jpg"),
                    "secondaryImageUrl": img("greenhouse.jpg"),
                    "badgeValue": "40k",
                    "badgeLabel": "Hectares under management",
                },
                {
                    "id": "agr-features",
                    "type": "features",
                    "title": "Why growers choose WBLester",
                    "intro": "Four reasons commercial farms keep us on retainer season after season.",
                    "items": [
                        {
                            "title": "Certified Agronomists",
                            "text": "Degree-qualified field scientists who walk your land every week, not once a year.",
                        },
                        {
                            "title": "Soil-First Planning",
                            "text": "Laboratory soil maps drive liming, fertiliser and tillage decisions before a seed is bought.",
                        },
                        {
                            "title": "Season-Long Support",
                            "text": "From land prep to harvest review with 24/7 livestock emergency cover in between.",
                        },
                        {
                            "title": "Proven Yield Gains",
                            "text": "Independent trials show 20\u201340% uplift within two seasons for managed clients.",
                        },
                    ],
                },
                {
                    "id": "agr-cards",
                    "type": "cards",
                    "kicker": "Specialist services",
                    "title": "Everything your operation needs",
                    "items": [
                        {
                            "title": "Soil Analysis & Land Prep",
                            "text": "Laboratory testing, liming plans and precision tillage that cut input waste.",
                            "slug": "soil-analysis",
                        },
                        {
                            "title": "Irrigation Systems",
                            "text": "Drip, pivot and sprinkler systems designed, installed and guaranteed.",
                            "slug": "irrigation-systems",
                        },
                        {
                            "title": "Veterinary Support",
                            "text": "24/7 herd health cover with digital records and rapid response.",
                            "slug": "veterinary-support",
                        },
                    ],
                },
                {
                    "id": "agr-steps",
                    "type": "steps",
                    "title": "How we work with you",
                    "intro": "A simple, transparent path from first visit to measurable results.",
                    "items": [
                        {
                            "title": "Free Farm Assessment",
                            "text": "An advisor walks your fields, tests your soil and reviews your herd records at no cost.",
                        },
                        {
                            "title": "Tailored Improvement Plan",
                            "text": "You receive a written plan with costs, timelines and projected yield gains per activity.",
                        },
                        {
                            "title": "On-Site Implementation",
                            "text": "Our crews execute \u2014 land prep, irrigation installs, planting protocols and herd programmes.",
                        },
                        {
                            "title": "Season Review & Reporting",
                            "text": "End-of-season audit compares actuals against targets so next season starts ahead.",
                        },
                    ],
                },
                {
                    "id": "agr-stats",
                    "type": "stats",
                    "backgroundImage": img("green-hills.jpg"),
                    "items": [
                        {"value": "500+", "label": "Farms supported"},
                        {"value": "40k", "label": "Hectares under management"},
                        {"value": "30%", "label": "Average yield uplift"},
                        {"value": "98%", "label": "Client retention"},
                    ],
                },
                {
                    "id": "agr-gallery",
                    "type": "gallery",
                    "kicker": "In the field",
                    "title": "Farming side by side with our clients",
                    "items": [
                        {"imageUrl": img("crops.jpg"), "caption": "Precision land preparation", "category": "Cropping"},
                        {"imageUrl": img("orchard.jpg"), "caption": "Orchard establishment", "category": "Horticulture"},
                        {"imageUrl": img("greenhouse.jpg"), "caption": "Protected cultivation nursery", "category": "Horticulture"},
                        {"imageUrl": img("irrigation-pivot.jpg"), "caption": "Centre-pivot installation", "category": "Infrastructure"},
                        {"imageUrl": img("livestock.jpg"), "caption": "Pasture-fed livestock programmes", "category": "Livestock"},
                        {"imageUrl": img("feedlot.jpg"), "caption": "Beef finishing on managed pasture", "category": "Livestock"},
                    ],
                },
                {
                    "id": "agr-testimonials",
                    "type": "testimonials",
                    "items": [
                        {
                            "quote": "We stopped guessing. Soil maps, variable liming and their irrigation design paid for themselves in one cotton crop.",
                            "name": "P. Nyoni",
                            "role": "Commercial grower",
                        },
                        {
                            "quote": "Their vet desk answered at 2am when we had downer cows. That response saved our season.",
                            "name": "L. Dube",
                            "role": "Dairy operation, 180-head herd",
                        },
                        {
                            "quote": "The pivot they installed cut our water bill by a third while lifting maize yields. Numbers don't lie.",
                            "name": "R. Mhike",
                            "role": "Irrigation client, 240 ha",
                        },
                    ],
                },
                {
                    "id": "agr-partners",
                    "type": "partners",
                    "items": [
                        {"label": "SeedCo"},
                        {"label": "AgriBank"},
                        {"label": "Farmers Union"},
                        {"label": "CropSafe Insurance"},
                        {"label": "Irrigation Association"},
                    ],
                },
                {
                    "id": "agr-cta",
                    "type": "cta",
                    "title": "Book your free farm assessment",
                    "text": "An advisor walks your land, tests your soil and leaves you a written improvement plan.",
                    "buttonLabel": "Request agricultural services",
                },
                {"id": "agr-contact", "type": "contactForm"},
            ],
        },

        102: {
            "blocks": [
                {
                    "id": "crop-hero",
                    "type": "hero",
                    "title": "Crop Farming & Advisory",
                    "subtitle": "Season-long agronomy support that more than pays for itself.",
                    "imageUrl": img("crops.jpg"),
                },
                {
                    "id": "crop-body",
                    "type": "richText",
                    "html": (
                        "<h2>What we deliver</h2>"
                        "<ul>"
                        "<li><strong>Crop planning</strong> — variety selection, planting calendars and gross-margin budgets before a seed is bought.</li>"
                        "<li><strong>Field monitoring</strong> — weekly scouting with geo-tagged, photo-documented reports.</li>"
                        "<li><strong>Input programmes</strong> — fertiliser, seed and crop protection sourced at contracted prices.</li>"
                        "<li><strong>Post-harvest</strong> — grading, storage and direct market linkage to vetted buyers.</li>"
                        "</ul>"
                        "<p>Clients typically see <strong>20–40% yield improvements</strong> "
                        "within two seasons — and know exactly why, because every "
                        "intervention is costed against its result.</p>"
                    ),
                },
                {
                    "id": "crop-steps",
                    "type": "steps",
                    "title": "Your season with us",
                    "items": [
                        {"title": "Soil first", "text": "Sampling and analysis before any input recommendation."},
                        {"title": "Plan & budget", "text": "A gross-margin plan you approve line by line."},
                        {"title": "Execute weekly", "text": "Scheduled operations with documented field visits."},
                        {"title": "Harvest & sell", "text": "Grading, storage and buyer introductions at market rates."},
                    ],
                },
                {
                    "id": "crop-sub",
                    "type": "cards",
                    "title": "Under this service",
                    "items": [
                        {
                            "title": "Soil Analysis & Land Preparation",
                            "text": "Know exactly what your soil needs before the rains come.",
                            "slug": "soil-analysis",
                        },
                        {
                            "title": "Irrigation Systems",
                            "text": "Design and install water infrastructure sized to your fields.",
                            "slug": "irrigation-systems",
                        },
                    ],
                },
                {
                    "id": "crop-cta",
                    "type": "cta",
                    "title": "Plan your most profitable season yet",
                    "buttonLabel": "Request crop advisory",
                },
                {"id": "crop-contact", "type": "contactForm"},
            ],
        },
        104: {
            "blocks": [
                {
                    "id": "soil-hero",
                    "type": "hero",
                    "title": "Soil Analysis & Land Preparation",
                    "subtitle": "Healthy soils are the cheapest input you will ever buy.",
                    "imageUrl": img("tree-planting.jpg"),
                },
                {
                    "id": "soil-body",
                    "type": "richText",
                    "html": (
                        "<h2>From sample to plan</h2>"
                        "<ol>"
                        "<li><strong>Grid or zone sampling</strong> of every management area on your farm.</li>"
                        "<li><strong>Accredited laboratory analysis</strong> of pH, NPK, CEC and micro-nutrients.</li>"
                        "<li><strong>A written fertility and liming programme</strong> with per-hectare costings.</li>"
                        "<li><strong>Mechanised ploughing, ripping and bedding</strong> executed to the plan on request.</li>"
                        "</ol>"
                        "<p>You receive interpretive reports — not just lab sheets — within "
                        "<strong>ten working days</strong>, and we revisit results after the season "
                        "to prove the response.</p>"
                    ),
                },
                {
                    "id": "soil-cta",
                    "type": "cta",
                    "title": "Test before you invest another dollar",
                    "buttonLabel": "Request soil testing",
                },
                {"id": "soil-contact", "type": "contactForm"},
            ],
        },
        105: {
            "blocks": [
                {
                    "id": "irr-hero",
                    "type": "hero",
                    "title": "Irrigation Systems",
                    "subtitle": "Water every hectare — efficiently, affordably, guaranteed.",
                    "imageUrl": img("greenhouse.jpg"),
                },
                {
                    "id": "irr-body",
                    "type": "richText",
                    "html": (
                        "<h2>Turnkey water solutions</h2>"
                        "<p>We survey your water source, model crop demand, design the "
                        "system, supply components, commission the installation and train "
                        "your team to run it. Options include <strong>drip lines, centre "
                        "pivots, sprinkler blocks and solar pumping</strong> sized to your "
                        "budget and power reality.</p>"
                        "<p>Every installation carries a <strong>two-year workmanship "
                        "warranty</strong>, and we stock spares locally so downtime is "
                        "measured in hours — not seasons.</p>"
                    ),
                },
                {
                    "id": "irr-cta",
                    "type": "cta",
                    "title": "Beat the next dry spell",
                    "buttonLabel": "Request an irrigation quote",
                },
                {"id": "irr-contact", "type": "contactForm"},
            ],
        },
        103: {
            "blocks": [
                {
                    "id": "live-hero",
                    "type": "hero",
                    "title": "Livestock & Poultry",
                    "subtitle": "Healthier herds, heavier weights, better margins.",
                    "imageUrl": img("livestock.jpg"),
                },
                {
                    "id": "live-body",
                    "type": "richText",
                    "html": (
                        "<h2>Complete animal production support</h2>"
                        "<ul>"
                        "<li><strong>Breeding programmes</strong> — sire selection and fertility management that compound herd quality.</li>"
                        "<li><strong>Nutrition &amp; feed formulation</strong> for cattle, goats and poultry at least-cost rationing.</li>"
                        "<li><strong>Housing, biosecurity &amp; welfare audits</strong> aligned to export-market expectations.</li>"
                        "<li><strong>Market-ready finishing</strong> — weight-gain programmes timed to buyer calendars.</li>"
                        "</ul>"
                        "<p>Herd records live in our digital system, so trends surface early "
                        "and decisions rest on data rather than memory.</p>"
                    ),
                },
                {
                    "id": "live-sub",
                    "type": "cards",
                    "title": "Under this service",
                    "items": [
                        {
                            "title": "Veterinary Support Services",
                            "text": "Vaccination drives, deworming and 24/7 emergency response.",
                            "slug": "veterinary-support",
                        }
                    ],
                },
                {
                    "id": "live-cta",
                    "type": "cta",
                    "title": "Grow your herd safely",
                    "buttonLabel": "Request livestock services",
                },
                {"id": "live-contact", "type": "contactForm"},
            ],
        },
        106: {
            "blocks": [
                {
                    "id": "vet-hero",
                    "type": "hero",
                    "title": "Veterinary Support Services",
                    "subtitle": "Prevention is cheaper than cure — we keep it that way.",
                    "imageUrl": img("livestock.jpg"),
                },
                {
                    "id": "vet-body",
                    "type": "richText",
                    "html": (
                        "<h2>Coverage when it counts</h2>"
                        "<p>Our veterinary partners run <strong>24/7 emergency "
                        "call-outs</strong> alongside scheduled vaccination drives, "
                        "deworming programmes and fertility services. Every visit is "
                        "logged digitally, building a herd-health history that flags "
                        "problems before they become mortalities.</p>"
                        "<p>Contract clients receive priority dispatch with a "
                        "<strong>six-hour response target</strong> inside our service radius.</p>"
                    ),
                },
                {
                    "id": "vet-cta",
                    "type": "cta",
                    "title": "Protect your animals around the clock",
                    "buttonLabel": "Request veterinary support",
                },
                {"id": "vet-contact", "type": "contactForm"},
            ],
        },

        # ------------------------------------------------------------------
        # REAL ESTATE
        # ------------------------------------------------------------------
        201: {
            "blocks": [
                {
                    "id": "re-hero",
                    "type": "hero",
                    "title": "Real Estate",
                    "subtitle": (
                        "Property done properly \u2014 sales, leasing, valuations and advice."
                    ),
                    "imageUrl": img("realestate-hero.jpg"),
                },
                {
                    "id": "re-intro",
                    "type": "about",
                    "kicker": "Your property partner",
                    "title": "From first viewing to final signature.",
                    "body": (
                        "<p>We handle residential and commercial transactions with "
                        "transparent fees, verified titles and rigorous due diligence \u2014 "
                        "the reason four in five of our clients come back or refer "
                        "someone else.</p>"
                    ),
                    "bullets": [
                        "Title verification completed before marketing begins",
                        "Professional photography and floor plans on every listing",
                        "Free appraisals backed by accredited valuation practice",
                    ],
                    "imageUrl": img("garden-estate.jpg"),
                    "secondaryImageUrl": img("listings.jpg"),
                    "badgeValue": "98%",
                    "badgeLabel": "Client retention rate",
                },
                {
                    "id": "re-features",
                    "type": "features",
                    "title": "Why clients list and buy with us",
                    "intro": "The safeguards that keep deals moving and surprises off the table.",
                    "items": [
                        {
                            "title": "Verified Titles",
                            "text": "Deed searches and due diligence completed before a property is ever marketed.",
                        },
                        {
                            "title": "Accredited Valuations",
                            "text": "Pricing grounded in International Valuation Standards \u2014 accepted by every major lender.",
                        },
                        {
                            "title": "Professional Marketing",
                            "text": "Photography, floor plans and targeted campaigns that put your property in front of qualified buyers.",
                        },
                        {
                            "title": "Conveyancing Support",
                            "text": "Our desk tracks registration to the last signature and keeps you informed weekly.",
                        },
                    ],
                },
                {
                    "id": "re-cards",
                    "type": "cards",
                    "kicker": "Popular services",
                    "title": "How can we help you move?",
                    "items": [
                        {
                            "title": "Residential Sales",
                            "text": "Family homes, stands and lifestyle properties matched to your brief.",
                            "slug": "residential-sales",
                        },
                        {
                            "title": "Commercial Leasing",
                            "text": "Offices, warehouses and retail positioned for growth.",
                            "slug": "commercial-leasing",
                        },
                        {
                            "title": "Investment Advisory",
                            "text": "Portfolio strategy modelled on yields, absorption and exits.",
                            "slug": "investment-advisory",
                        },
                    ],
                },
                {
                    "id": "re-steps",
                    "type": "steps",
                    "title": "Your journey with us",
                    "intro": "A clear process from first conversation to keys in hand.",
                    "items": [
                        {
                            "title": "Valuation & Brief",
                            "text": "We appraise your property free of charge and define exactly what success looks like.",
                        },
                        {
                            "title": "Shortlist & Viewings",
                            "text": "Buyers receive curated matches within 48 hours; sellers get pre-screened viewers only.",
                        },
                        {
                            "title": "Offer & Negotiation",
                            "text": "Skilled negotiators secure the best terms while lawyers verify title in parallel.",
                        },
                        {
                            "title": "Registration & Handover",
                            "text": "We track registration weekly until transfer completes and keys change hands.",
                        },
                    ],
                },
                {
                    "id": "re-stats",
                    "type": "stats",
                    "backgroundImage": img("valuations.jpg"),
                    "items": [
                        {"value": "450+", "label": "Properties sold & leased"},
                        {"value": "120+", "label": "Active listings today"},
                        {"value": "21", "label": "Days average time to lease"},
                        {"value": "98%", "label": "Client retention"},
                    ],
                },
                {
                    "id": "re-gallery",
                    "type": "gallery",
                    "kicker": "Recently placed",
                    "title": "Properties we have matched",
                    "items": [
                        {"imageUrl": img("garden-estate.jpg"), "caption": "Executive residence with landscaped grounds", "category": "Residential"},
                        {"imageUrl": img("listings.jpg"), "caption": "Family suburb sales", "category": "Residential"},
                        {"imageUrl": img("interior.jpg"), "caption": "Designer interiors that sell homes faster", "category": "Interiors"},
                        {"imageUrl": img("realestate-hero.jpg"), "caption": "Modern builds at dusk", "category": "Residential"},
                        {"imageUrl": img("valuations.jpg"), "caption": "Commercial leasing mandates", "category": "Commercial"},
                        {"imageUrl": img("landscaping.jpg"), "caption": "Lifestyle estates with established gardens", "category": "Lifestyle"},
                    ],
                },
                {
                    "id": "re-testimonials",
                    "type": "testimonials",
                    "items": [
                        {
                            "quote": "Eleven weeks from offer to registration, with weekly updates the whole way. Effortless.",
                            "name": "T. Banda",
                            "role": "Residential buyer",
                        },
                        {
                            "quote": "They leased our warehouse in three weeks at above asking rent. Their tenant screening is worth every cent.",
                            "name": "M. Patel",
                            "role": "Commercial landlord",
                        },
                        {
                            "quote": "Their valuation was within 2% of the final sale price. We listed with confidence and sold in five weeks.",
                            "name": "S. Chirwa",
                            "role": "Residential seller",
                        },
                    ],
                },
                {
                    "id": "re-partners",
                    "type": "partners",
                    "items": [
                        {"label": "MortgageLink"},
                        {"label": "Conveyance Direct"},
                        {"label": "HomeSure Insurance"},
                        {"label": "Chamber of Commerce"},
                        {"label": "BuildSociety Bank"},
                    ],
                },
                {
                    "id": "re-cta",
                    "type": "cta",
                    "title": "Buying, selling or leasing?",
                    "text": "Speak to an advisor today and get a free property appraisal.",
                    "buttonLabel": "Request real estate services",
                },
                {"id": "re-contact", "type": "contactForm"},
            ],
        },

        202: {
            "blocks": [
                {
                    "id": "list-hero",
                    "type": "hero",
                    "title": "Property Listings",
                    "subtitle": "Every listing verified — title deeds checked, sites inspected.",
                    "imageUrl": img("listings.jpg"),
                },
                {
                    "id": "list-body",
                    "type": "richText",
                    "html": (
                        "<h2>Why our listings close faster</h2>"
                        "<ul>"
                        "<li>Professional photography and measured floor plans on every listing.</li>"
                        "<li>Title verification completed <strong>before</strong> marketing begins — no late surprises.</li>"
                        "<li>Qualified-buyer pre-screening saves sellers weekends of tyre-kickers.</li>"
                        "<li>New stock arrives weekly; matching buyers are alerted first.</li>"
                        "</ul>"
                        "<p>Tell us what you need — budget, area, must-haves — and we will "
                        "shortlist within 48 hours.</p>"
                    ),
                },
                {
                    "id": "list-sub",
                    "type": "cards",
                    "title": "Browse by type",
                    "items": [
                        {
                            "title": "Residential Sales",
                            "text": "Starter homes to executive residences.",
                            "slug": "residential-sales",
                        },
                        {
                            "title": "Commercial Leasing",
                            "text": "Space that fits your business plan.",
                            "slug": "commercial-leasing",
                        },
                    ],
                },
                {
                    "id": "list-cta",
                    "type": "cta",
                    "title": "Looking for something specific?",
                    "buttonLabel": "Send us your requirements",
                },
                {"id": "list-contact", "type": "contactForm"},
            ],
        },
        204: {
            "blocks": [
                {
                    "id": "res-hero",
                    "type": "hero",
                    "title": "Residential Sales",
                    "subtitle": "Find the home that fits your family and your budget.",
                    "imageUrl": img("garden-estate.jpg"),
                },
                {
                    "id": "res-body",
                    "type": "richText",
                    "html": (
                        "<h2>Guided buying, start to finish</h2>"
                        "<p>We shortlist strictly against your brief, arrange viewings "
                        "around your schedule and negotiate hard on your behalf. Our "
                        "conveyancing desk tracks registration until keys are in your "
                        "hand — and answers the phone while they do it.</p>"
                        "<p>Sellers receive a <strong>free valuation</strong>, staging "
                        "advice and a marketing plan <em>before</em> signing anything. "
                        "No upfront fees — we earn on success.</p>"
                    ),
                },
                {
                    "id": "res-cta",
                    "type": "cta",
                    "title": "Your next chapter starts with a viewing",
                    "buttonLabel": "Request a consultation",
                },
                {"id": "res-contact", "type": "contactForm"},
            ],
        },
        205: {
            "blocks": [
                {
                    "id": "com-hero",
                    "type": "hero",
                    "title": "Commercial Leasing",
                    "subtitle": "Premises positioned for growth.",
                    "imageUrl": img("valuations.jpg"),
                },
                {
                    "id": "com-body",
                    "type": "richText",
                    "html": (
                        "<h2>Space strategy, simplified</h2>"
                        "<p>Office parks, high-street retail, industrial yards and "
                        "warehousing — we match footfall, logistics and zoning to your "
                        "operations, then negotiate rates, escalations and fit-out "
                        "periods that protect your cash flow.</p>"
                        "<p>Landlords: our vetted tenant pipeline and triple-net lease "
                        "templates keep vacancy short and administration lighter.</p>"
                    ),
                },
                {
                    "id": "com-cta",
                    "type": "cta",
                    "title": "Relocating or expanding?",
                    "buttonLabel": "Request commercial options",
                },
                {"id": "com-contact", "type": "contactForm"},
            ],
        },
        203: {
            "blocks": [
                {
                    "id": "val-hero",
                    "type": "hero",
                    "title": "Valuations & Consultancy",
                    "subtitle": "Independent numbers you can take to the bank — literally.",
                    "imageUrl": img("valuations.jpg"),
                },
                {
                    "id": "val-body",
                    "type": "richText",
                    "html": (
                        "<h2>Accredited valuation practice</h2>"
                        "<ul>"
                        "<li>Mortgage and insurance valuations accepted by all major lenders.</li>"
                        "<li>Rental determinations and arbitration support that hold up under cross-examination.</li>"
                        "<li>Portfolio reviews for funds, trusts and family offices.</li>"
                        "</ul>"
                        "<p>Reports follow <strong>International Valuation Standards</strong> "
                        "and are typically delivered within five working days — with the "
                        "analyst available to defend the numbers.</p>"
                    ),
                },
                {
                    "id": "val-sub",
                    "type": "cards",
                    "title": "Under this service",
                    "items": [
                        {
                            "title": "Investment Advisory",
                            "text": "Where to deploy capital for risk-adjusted returns.",
                            "slug": "investment-advisory",
                        }
                    ],
                },
                {
                    "id": "val-cta",
                    "type": "cta",
                    "title": "Know exactly what your asset is worth",
                    "buttonLabel": "Request a valuation",
                },
                {"id": "val-contact", "type": "contactForm"},
            ],
        },
        206: {
            "blocks": [
                {
                    "id": "inv-hero",
                    "type": "hero",
                    "title": "Investment Advisory",
                    "subtitle": "Property decisions driven by evidence, not hype.",
                    "imageUrl": img("listings.jpg"),
                },
                {
                    "id": "inv-body",
                    "type": "richText",
                    "html": (
                        "<h2>Data-first portfolio building</h2>"
                        "<p>We model rental yields, absorption rates and exit scenarios "
                        "before you commit a cent. Advisory covers single assets through "
                        "mixed-use developments, with quarterly performance reviews that "
                        "keep strategy honest.</p>"
                        "<p>Clients gain access to off-market opportunities surfaced by "
                        "our listings desk months before public release.</p>"
                    ),
                },
                {
                    "id": "inv-cta",
                    "type": "cta",
                    "title": "Invest with confidence",
                    "buttonLabel": "Book an advisory session",
                },
                {"id": "inv-contact", "type": "contactForm"},
            ],
        },

        # ------------------------------------------------------------------
        # NATURAL RESOURCES & ENERGY
        # ------------------------------------------------------------------
        301: {
            "blocks": [
                {
                    "id": "en-hero",
                    "type": "hero",
                    "title": "Natural Resources & Energy",
                    "subtitle": (
                        "Powering industry responsibly \u2014 minerals, sun and wind."
                    ),
                    "imageUrl": img("energy-hero.jpg"),
                },
                {
                    "id": "en-intro",
                    "type": "about",
                    "kicker": "Resources with responsibility",
                    "title": "Projects that survive scrutiny.",
                    "body": (
                        "<p>We develop mineral and renewable projects to international "
                        "ESG standards, partnering communities at every step \u2014 because "
                        "a project without a social licence is just a liability.</p>"
                    ),
                    "bullets": [
                        "Exploration through permitting handled in-house",
                        "Bankable feasibility inputs investors recognise",
                        "Community frameworks that de-risk operations",
                    ],
                    "imageUrl": img("solar-install.jpg"),
                    "secondaryImageUrl": img("mining.jpg"),
                    "badgeValue": "ESG",
                    "badgeLabel": "International standards applied",
                },
                {
                    "id": "en-features",
                    "type": "features",
                    "title": "Built for bankability",
                    "intro": "The disciplines that turn ground and sunlight into financeable projects.",
                    "items": [
                        {
                            "title": "ESG-Compliant Design",
                            "text": "International frameworks applied from day one \u2014 not retrofitted for lenders later.",
                        },
                        {
                            "title": "In-House Permitting",
                            "text": "Our legal desk secures licences, renewals and transfers without third-party delays.",
                        },
                        {
                            "title": "Bankable Studies",
                            "text": "Feasibility inputs structured for investor due diligence and lender credit committees.",
                        },
                        {
                            "title": "Community Partnership",
                            "text": "Engagement frameworks that earn and keep the social licence projects depend on.",
                        },
                    ],
                },
                {
                    "id": "en-cards",
                    "type": "cards",
                    "kicker": "Specialist services",
                    "title": "Two disciplines, one standard",
                    "items": [
                        {
                            "title": "Mineral Exploration & Licensing",
                            "text": "Ground surveys through to permits, secured and maintained.",
                            "slug": "mineral-exploration",
                        },
                        {
                            "title": "Solar Solutions",
                            "text": "Grid-tied and off-grid PV engineered to your load profile.",
                            "slug": "solar-solutions",
                        },
                        {
                            "title": "Wind Farm Development",
                            "text": "Met-mast campaigns through turbine selection and grid studies.",
                            "slug": "wind-farms",
                        },
                    ],
                },
                {
                    "id": "en-steps",
                    "type": "steps",
                    "title": "From prospect to power",
                    "intro": "One accountable team across every phase of the project lifecycle.",
                    "items": [
                        {
                            "title": "Feasibility Screening",
                            "text": "No-obligation technical review tells you quickly whether your ground or site has merit.",
                        },
                        {
                            "title": "Assessment & Permitting",
                            "text": "Resource studies, environmental management and licence applications run in parallel.",
                        },
                        {
                            "title": "Financing & EPC Delivery",
                            "text": "We structure funding and manage engineering, procurement and construction to budget.",
                        },
                        {
                            "title": "Operate & Monitor",
                            "text": "Remote monitoring, monthly performance reporting and O&M contracts that stand behind yields.",
                        },
                    ],
                },
                {
                    "id": "en-stats",
                    "type": "stats",
                    "backgroundImage": img("wind-farm.jpg"),
                    "items": [
                        {"value": "120+", "label": "MW clean capacity developed"},
                        {"value": "30+", "label": "Exploration licences secured"},
                        {"value": "40k", "label": "Tonnes CO\u2082 offset annually"},
                        {"value": "12", "label": "Communities partnered"},
                    ],
                },
                {
                    "id": "en-gallery",
                    "type": "gallery",
                    "kicker": "On site",
                    "title": "Work in progress",
                    "items": [
                        {"imageUrl": img("energy-hero.jpg"), "caption": "Hybrid solar-wind plant", "category": "Renewables"},
                        {"imageUrl": img("solar-install.jpg"), "caption": "Rooftop PV installation", "category": "Solar"},
                        {"imageUrl": img("wind-farm.jpg"), "caption": "Turbine string on ridgeline", "category": "Wind"},
                        {"imageUrl": img("mining.jpg"), "caption": "Compliant extraction operations", "category": "Mining"},
                        {"imageUrl": img("tree-planting.jpg"), "caption": "Mine-site rehabilitation programme", "category": "Environment"},
                        {"imageUrl": img("nature-reserve.jpg"), "caption": "Watershed protection partnership", "category": "Environment"},
                    ],
                },
                {
                    "id": "en-testimonials",
                    "type": "testimonials",
                    "items": [
                        {
                            "quote": "They took our prospecting order through renewal and transfer while their geologists built a resource model investors actually funded.",
                            "name": "D. Kanyemba",
                            "role": "Mineral rights holder",
                        },
                        {
                            "quote": "Our 1.2 MW plant performs within 3% of the model they signed. Monthly reports arrive like clockwork.",
                            "name": "K. Mutasa",
                            "role": "Factory owner, C&I solar client",
                        },
                        {
                            "quote": "Their community framework turned our biggest project risk into our strongest reference.",
                            "name": "A. Sibanda",
                            "role": "Wind farm developer",
                        },
                    ],
                },
                {
                    "id": "en-partners",
                    "type": "partners",
                    "items": [
                        {"label": "GridWorks Utility"},
                        {"label": "Green Finance Corp"},
                        {"label": "Miners Association"},
                        {"label": "EcoCert Global"},
                        {"label": "TerraSurvey Ltd"},
                    ],
                },
                {
                    "id": "en-cta",
                    "type": "cta",
                    "title": "Have ground or a project idea?",
                    "text": "Our technical team offers no-obligation feasibility screenings.",
                    "buttonLabel": "Request energy services",
                },
                {"id": "en-contact", "type": "contactForm"},
            ],
        },

        302: {
            "blocks": [
                {
                    "id": "min-hero",
                    "type": "hero",
                    "title": "Mining & Minerals",
                    "subtitle": "From grassroots exploration to profitable, compliant operation.",
                    "imageUrl": img("mining.jpg"),
                },
                {
                    "id": "min-body",
                    "type": "richText",
                    "html": (
                        "<h2>Full-cycle mining services</h2>"
                        "<ul>"
                        "<li>Geological mapping, sampling and resource estimation.</li>"
                        "<li>Environmental impact management and genuine community engagement.</li>"
                        "<li>Permitting, compliance and safety systems auditors accept.</li>"
                        "<li>Offtake introductions with vetted international buyers.</li>"
                        "</ul>"
                        "<p>We measure ourselves on one number: how quickly your ground "
                        "moves from prospect to permitted production — legally and "
                        "without community conflict.</p>"
                    ),
                },
                {
                    "id": "min-sub",
                    "type": "cards",
                    "title": "Under this service",
                    "items": [
                        {
                            "title": "Mineral Exploration & Licensing",
                            "text": "Secure tenure and de-risk your ground.",
                            "slug": "mineral-exploration",
                        }
                    ],
                },
                {
                    "id": "min-cta",
                    "type": "cta",
                    "title": "Unlock your ground's value",
                    "buttonLabel": "Request mining services",
                },
                {"id": "min-contact", "type": "contactForm"},
            ],
        },
        304: {
            "blocks": [
                {
                    "id": "exp-hero",
                    "type": "hero",
                    "title": "Mineral Exploration & Licensing",
                    "subtitle": "Know what lies beneath — legally and technically.",
                    "imageUrl": img("mining.jpg"),
                },
                {
                    "id": "exp-body",
                    "type": "richText",
                    "html": (
                        "<h2>De-risking exploration</h2>"
                        "<p>Our geologists combine remote sensing, geophysics and "
                        "systematic trenching to build credible target models, while our "
                        "legal desk secures and maintains your exclusive prospecting "
                        "orders — including renewals, transfers and dispute defence.</p>"
                        "<p>The result: investor-grade reports grounded in real tenure "
                        "security, ready for due diligence.</p>"
                    ),
                },
                {
                    "id": "exp-cta",
                    "type": "cta",
                    "title": "Start your exploration right",
                    "buttonLabel": "Request exploration support",
                },
                {"id": "exp-contact", "type": "contactForm"},
            ],
        },
        303: {
            "blocks": [
                {
                    "id": "ren-hero",
                    "type": "hero",
                    "title": "Renewable Energy Projects",
                    "subtitle": "Clean power that pays back — engineered for African conditions.",
                    "imageUrl": img("energy-hero.jpg"),
                },
                {
                    "id": "ren-body",
                    "type": "richText",
                    "html": (
                        "<h2>Solar and wind, end to end</h2>"
                        "<p>We develop utility-scale and commercial &amp; industrial "
                        "renewables: feasibility studies, licensing, EPC management, "
                        "financing structuring and long-term O&amp;M contracts — one "
                        "accountable partner across the lifecycle.</p>"
                        "<p>Every plant ships with a performance model we stand behind, "
                        "monitored remotely and reported monthly.</p>"
                    ),
                },
                {
                    "id": "ren-sub",
                    "type": "cards",
                    "title": "Under this service",
                    "items": [
                        {
                            "title": "Solar Solutions",
                            "text": "Rooftop, ground-mount and hybrid PV plants.",
                            "slug": "solar-solutions",
                        },
                        {
                            "title": "Wind Farm Development",
                            "text": "Met-mast campaigns through turbine selection.",
                            "slug": "wind-farms",
                        },
                    ],
                },
                {
                    "id": "ren-cta",
                    "type": "cta",
                    "title": "Cut your energy bills permanently",
                    "buttonLabel": "Request a renewable assessment",
                },
                {"id": "ren-contact", "type": "contactForm"},
            ],
        },
        305: {
            "blocks": [
                {
                    "id": "sol-hero",
                    "type": "hero",
                    "title": "Solar Solutions",
                    "subtitle": "Sunlight is the only input your plant will ever need.",
                    "imageUrl": img("energy-hero.jpg"),
                },
                {
                    "id": "sol-body",
                    "type": "richText",
                    "html": (
                        "<h2>Systems sized to your load profile</h2>"
                        "<p>Using twelve months of metering data we design photovoltaic "
                        "plants — with storage where it earns its keep — that typically "
                        "cut electricity costs by <strong>30–60%</strong>. Performance is "
                        "guaranteed under an availability warranty, monitored remotely "
                        "and reported monthly in plain language.</p>"
                    ),
                },
                {
                    "id": "sol-cta",
                    "type": "cta",
                    "title": "Get a free solar study",
                    "buttonLabel": "Request a solar proposal",
                },
                {"id": "sol-contact", "type": "contactForm"},
            ],
        },
        306: {
            "blocks": [
                {
                    "id": "win-hero",
                    "type": "hero",
                    "title": "Wind Farm Development",
                    "subtitle": "Turning viable wind corridors into revenue.",
                    "imageUrl": img("energy-hero.jpg"),
                },
                {
                    "id": "win-body",
                    "type": "richText",
                    "html": (
                        "<h2>Development without the guesswork</h2>"
                        "<p>Minimum twelve-month met-mast measurement campaigns, "
                        "bankable yield assessments, grid connection studies and "
                        "community benefit-sharing frameworks — the full "
                        "pre-construction package that lenders expect.</p>"
                    ),
                },
                {
                    "id": "win-cta",
                    "type": "cta",
                    "title": "Assess your wind resource",
                    "buttonLabel": "Request a wind feasibility study",
                },
                {"id": "win-contact", "type": "contactForm"},
            ],
        },
    }
    return content.get(page_id)


def slugify(value: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in value.lower()).strip("-")


def _seo_description(page_id: int, title: str) -> str:
    descriptions = {
        100: "WBLester & O — integrated agriculture, real estate and natural resources & energy services. Request a service today.",
    }
    return descriptions.get(
        page_id, f"{title} — professional services by WBLester & O."
    )


def _seed_pages() -> None:
    for page_id, category_id, parent_id, slug, title, sort_order, hero_image in PAGES:
        existing = Pages.objects(page_id=page_id).first()
        if existing:
            continue
        Pages(
            page_id=page_id,
            category_id=category_id,
            parent_id=parent_id,
            title=title,
            slug=slug,
            content_json=_blocks(page_id) or {"blocks": []},
            visible=True,  # home content is served anonymously via /public/content
            sort_order=sort_order,
            seo_title=f"{title} | WBLester & O",
            seo_description=_seo_description(page_id, title),
        ).save()


def _seed_mail_templates() -> None:
    templates = {
        "contact": (
            "<h2>New service request</h2>"
            "<p><b>From:</b> {{name}} &lt;{{email}}&gt;</p>"
            "<p><b>Subject:</b> {{subject}}</p>"
            "<p>{{body}}</p>"
        ),
        "reply": (
            "<p>Dear {{name}},</p>"
            "<p>{{body}}</p>"
            "<p>Kind regards,<br/>WBLester &amp; O Team</p>"
        ),
    }
    for name, contents in templates.items():
        if MailTemplates.objects(template_name=name).first():
            continue
        MailTemplates(template_id=next_id(MailTemplates, "template_id"), template_name=name, description=f"Default {name} template", contents=contents).save()


if __name__ == "__main__":
    import mongoengine

    from .config import Config

    username = os.environ.get("MONGODB_USERNAME")
    password = os.environ.get("MONGODB_PASSWORD")
    kwargs = {"uuidRepresentation": "standard"}
    if username and password:
        kwargs["username"] = username
        kwargs["password"] = password
        kwargs["authentication_source"] = os.environ.get(
            "MONGODB_AUTH_SOURCE", "admin"
        )
    mongoengine.connect(
        host=os.environ.get("MONGODB_HOST", "mongo"),
        port=int(os.environ.get("MONGODB_PORT", "27017")),
        db=os.environ.get("MONGODB_DB", "wblester"),
        **kwargs,
    )
    RUNTIME_CONFIG["UPLOAD_DIR"] = os.environ.get(
        "UPLOAD_DIR", Config.UPLOAD_DIR
    )
    RUNTIME_CONFIG["PUBLIC_BASE_URL"] = os.environ.get(
        "PUBLIC_BASE_URL", Config.PUBLIC_BASE_URL
    )
    seed()
