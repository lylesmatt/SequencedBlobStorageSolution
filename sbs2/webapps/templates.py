from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, List, Union

from bottle import template

from sbs2 import _copy_fileobj


@dataclass
class NavBarLink:
    label: str
    url: str


@dataclass
class NavBarDropDown:
    label: str
    url: str = field(default='#')
    sub_links: List[NavBarLink] = field(default_factory=list)


NavBarItem = Union[NavBarLink, NavBarDropDown]


class _TemplateCache:
    def __init__(self) -> None:
        # keeping a reference to the temporary directory, so it will not be removed
        self._template_temp_dir = TemporaryDirectory()
        self._templates_resources = files('sbs2.webapps')
        self.template_lookup = [self._template_temp_dir.name]

    def ensure_template_loaded(self, template_name: str) -> None:
        template_temp_path = Path(self._template_temp_dir.name).joinpath(template_name).with_suffix('.tpl')
        if not template_temp_path.exists():
            resource = self._templates_resources.joinpath(template_temp_path.name)
            with resource.open('rb') as src, template_temp_path.open('wb') as dest:
                _copy_fileobj(src, dest)


@dataclass
class _BaseVars:
    title: str
    nav_bar_items: List[NavBarItem]


class TemplateContext:
    def __init__(self) -> None:
        self._nav_bar_items: List[NavBarItem] = list()
        self._template_cache = _TemplateCache()
        self._template_cache.ensure_template_loaded('base')

    def add_to_nav_bar(self, item: NavBarItem) -> None:
        self._nav_bar_items.append(item)

    def render_template(self, template_name: str, title: str, **template_vars: Any) -> str:
        self._template_cache.ensure_template_loaded(template_name)
        base_vars = _BaseVars(title=title, nav_bar_items=self._nav_bar_items)
        render = template(
            template_name,
            base_vars=base_vars,
            template_lookup=self._template_cache.template_lookup,
            **template_vars
        )
        return render
