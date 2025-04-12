import bs4
from . import bs

DOCTYPE = "<!doctype html>"


class Formatter:
    def __init__(self, config):
        self.non_closing = config.non_closing_tags
        self.no_indent = config.no_indent_tags

    def format_attrs(self, el):
        attrs = ""
        orig = getattr(el, "attrs", {}) or {}
        if orig:
            for key, vals in orig.items():
                vals = " ".join(vals) if isinstance(vals, (list, tuple)) else vals  # noqa
                attrs += ' {}="{}"'.format(key, vals)

        return attrs

    def format_element(self, el, lines, depth=0, prefix="    "):
        indent = prefix * depth
        if bs.is_navigable_string(el):
            el = f"<!-- {el} -->" if bs.is_comment(el) else el.strip()
            if el:
                lines.append("{}{}".format(indent, el))

            return lines

        line = "{}<{}{}>".format(indent, el.name, self.format_attrs(el))
        if el.name in self.non_closing:
            lines.append(line)
            return lines

        n_children = len(el.contents)
        if n_children:
            if n_children > 1 or isinstance(el.contents[0], bs4.Tag):
                lines.append(line)
                for ct in el.contents:
                    ct_depth = depth if ct.name in self.no_indent else depth + 1
                    lines = self.format_element(ct, lines, ct_depth, prefix)
                lines.append("{}</{}>".format(indent, el.name))
            else:
                lines.append("{}{}</{}>".format(line, el.contents[0].strip(), el.name))
        else:
            lines.append("{}</{}>".format(line, el.name))

        return lines

    def __call__(self, el, depth=0, prefix="    ", doctype=False):
        lines = []
        assert isinstance(el, (list, tuple, bs4.BeautifulSoup))
        if isinstance(el, (list, tuple)):
            contents = el

        elif isinstance(el, bs4.BeautifulSoup):
            if not el.contents:
                return ""

            contents = iter(el.contents)
            if doctype:
                lines.append(DOCTYPE)

            if isinstance(el.contents[0], bs4.Doctype):
                next(contents)

        for child in contents:
            lines = self.format_element(child, lines, depth, prefix)

        return "\n".join(lines)
