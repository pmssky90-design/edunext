from dataclasses import dataclass, field


@dataclass
class Region:
    key: str
    name: str
    slug: str
    level: str
    parent: str | None = None
    children: list[str] = field(default_factory=list)


@dataclass
class Page:
    slug: str
    title: str
    page_type: str
    category: str
    seo_title: str = ""
    region_key: str | None = None
    parent_slug: str | None = None
    child_slugs: list[str] = field(default_factory=list)
    sibling_slugs: list[str] = field(default_factory=list)
    related_slugs: list[str] = field(default_factory=list)
    school_slugs: list[str] = field(default_factory=list)
    school_display_name: str = ""
    official_school_name: str = ""
    hero_image: str = ""
    hero_image_alt: str = ""
    search_thumbnail: str = ""
    search_thumbnail_url: str = ""
    search_thumbnail_hash: str = ""
    body: str = ""
    meta_description: str = ""
    breadcrumbs: list[tuple[str, str]] = field(default_factory=list)

    @property
    def url(self) -> str:
        if self.slug == "index":
            return "/"
        return f"/{self.slug}/"

    @property
    def canonical_path(self) -> str:
        return self.url
