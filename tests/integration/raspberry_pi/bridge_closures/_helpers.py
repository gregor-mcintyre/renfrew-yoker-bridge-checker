"""Webpage bodies and responses shared by the bridge closure integration tests."""

from curl_cffi import requests

from tests import closures_webpage_text

_CLOSURE_NOTICE = (
    "The Renfrew Bridge will be closed to both road and pedestrian traffic during the "
    "following times:"
)

PAGE_WITHOUT_CLOSURE = f"""
<div class="article">
  <h3>{closures_webpage_text.DATE_HEADING}</h3>
  <p>{closures_webpage_text.NO_CLOSURES_LINE}</p>
</div>
"""

PAGE_WITH_CLOSURE = f"""
<div class="article">
  <h3>{closures_webpage_text.DATE_HEADING}</h3>
  <p>{_CLOSURE_NOTICE}</p>
  <p>{closures_webpage_text.TIME_RANGE}</p>
</div>
"""


def build_response(body: str = "", *, status_code: int = 200) -> requests.Response:
    """Builds a `Response` for the patched `requests.get` to return.

    `ok` is set from `status_code` as a real request sets it, since `Response`
    otherwise leaves it `True`.

    Args:
        body: The HTML response body.
        status_code: The HTTP status code of the response.

    Returns:
        The response, with `body` as the content and `status_code` as the status.
    """
    response = requests.Response()
    response.status_code = status_code
    response.ok = 200 <= status_code < 400
    response.content = body.encode()

    return response
