import typing
from urllib.parse import ParseResult, urlparse

from jinja2 import Undefined, contextfunction, escape
from starlette.templating import Jinja2Templates


def render_ql_nickname(nickname):
    nickname = str(escape(nickname))
    for i in range(8):
        nickname = nickname.replace(
            "^" + str(i), '</span><span class="qc' + str(i) + '">'
        )
    return '<span class="qc7">' + nickname + "</span>"


def seconds_to_mmss(value):
    seconds = int(escape(value))
    m, s = divmod(seconds, 60)
    return "%02d:%02d" % (m, s)


class Templates(Jinja2Templates):
    def __init__(self, directory: str) -> None:
        @contextfunction
        def url_for(context: dict, name: str, **path_params: typing.Any) -> str:
            request = context["request"]
            path_params = {
                k: v
                for k, v in path_params.items()
                if not isinstance(v, Undefined) and v is not None
            }
            # NOTE: take this stupid hack away, when url_for returns relative path
            absolute_url = request.url_for(name, **path_params)
            parsed_absolute_url = urlparse(absolute_url)
            return ParseResult("", "", *parsed_absolute_url[2:]).geturl()

        super().__init__(directory)
        self.env.filters["ql_nickname"] = render_ql_nickname
        self.env.filters["seconds_to_mmss"] = seconds_to_mmss
        self.env.globals["url_for"] = url_for


templates = Templates(directory="templates")
