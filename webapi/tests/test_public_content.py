"""Tests for GET /public/content (anonymous website content feed)."""

from wblester_api.models import Categories, Pages, SiteSettings


def _seed_content():
    Categories(
        category_id=1,
        category_name="Agriculture",
        slug="agriculture",
        visible=True,
        sort_order=1,
    ).save()
    Categories(
        category_id=2,
        category_name="Hidden Cat",
        slug="hidden-cat",
        visible=False,
        sort_order=2,
    ).save()
    Pages(
        page_id=100,
        title="Home",
        slug="home",
        visible=False,
        sort_order=0,
        content_json={"blocks": [{"type": "jumbotron", "slides": []}]},
        seo_title="Home SEO",
    ).save()
    Pages(
        page_id=101,
        category_id=1,
        title="Farming",
        slug="farming",
        visible=True,
        sort_order=1,
        content_json={"blocks": [{"type": "richText", "html": "<p>hi</p>"}]},
        seo_title="Farming SEO",
        seo_description="Farm desc",
    ).save()
    if SiteSettings.objects.count() == 0:
        SiteSettings(
            settings_id=1,
            site_name="WBLESTER & O",
            site_title="WBLESTER & O",
            address="1 Green Way",
            email="hello@wblester.local",
            phone_number="+1 555 0100",
            secret_key="must-not-leak",
            decryption_password="must-not-leak",
        ).save()


def test_public_content_requires_no_auth(client):
    resp = client.get("/public/content")
    assert resp.status_code == 200
    body = resp.get_json()
    assert set(body) >= {"categories", "pages", "settings", "fetchedAt"}


def test_public_content_only_visible_records(client):
    _seed_content()
    body = client.get("/public/content").get_json()

    cat_slugs = [c["slug"] for c in body["categories"]]
    assert cat_slugs == ["agriculture"]

    page_slugs = [p["slug"] for p in body["pages"]]
    assert "home" not in page_slugs
    assert "farming" in page_slugs


def test_public_content_page_shape_and_blocks(client):
    _seed_content()
    body = client.get("/public/content").get_json()
    farming = next(p for p in body["pages"] if p["slug"] == "farming")
    assert farming["pageId"] == 101
    assert farming["categoryId"] == 1
    assert farming["seoTitle"] == "Farming SEO"
    assert farming["contentJson"]["blocks"][0]["type"] == "richText"


def test_public_content_settings_whitelist(client):
    _seed_content()
    body = client.get("/public/content").get_json()
    s = body["settings"]
    assert s["siteName"] == "WBLESTER & O"
    assert s["phoneNumber"] == "+1 555 0100"
    assert "secretKey" not in s
    assert "decryptionPassword" not in s
