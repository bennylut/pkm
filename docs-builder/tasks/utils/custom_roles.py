from typing import Dict, Any, List, Optional, Tuple

from docutils import nodes
from docutils.parsers.rst.states import Inliner
from sphinx.application import Sphinx


def add_class_role(spx: Sphinx, name: str, classes: List[str]):
    def cls_rule(
            name: str, rawtext: str, text: str, lineno: int, inliner: Inliner,
            options: Optional[Dict[str, Any]] = None, content: Optional[List[str]] = None
    ) -> Tuple[List, List[str]]:
        """
        :see: https://docutils.sourceforge.io/docs/howto/rst-roles.html
        """

        node = nodes.inline(rawtext, text, classes=classes)
        return [node], []

    spx.add_role(name, cls_rule)


def initialize_css_roles(spx: Sphinx, config):
    added_roles = []
    for clsrl in spx.config.class_roles:
        if isinstance(clsrl, str):
            rl, cls = clsrl, [clsrl]
        else:
            rl, cls = clsrl[0], clsrl[1:]
        
        add_class_role(spx, rl, cls)
        added_roles.append(rl)
        
    print(f"class roles added: {added_roles}")


def setup(spx: Sphinx):
    spx.add_config_value("class_roles", [], True)
    spx.connect('config-inited', initialize_css_roles)
