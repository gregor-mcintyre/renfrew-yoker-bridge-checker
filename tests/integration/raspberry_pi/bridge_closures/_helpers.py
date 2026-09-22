"""Webpage bodies and responses shared by the bridge closure integration tests."""

import requests

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
    """Builds a `requests.Response` for the patched `requests.get` to return.

    Args:
        body: The HTML response body.
        status_code: The HTTP status code of the response.

    Returns:
        A `requests.Response` with `body` as its content and `status_code` as its
        status.
    """
    response = requests.Response()
    response.status_code = status_code
    response._content = body.encode()

    return response
