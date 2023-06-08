from mindsdb.integrations.libs.const import HANDLER_TYPE

from .__about__ import __version__ as version, __description__ as description

try:
    from .stripe_handler import StripeHandler as Handler

    import_error = None
except Exception as e:
    Handler = None
    import_error = e

title = "Stripe"
name = "stripe"
type = HANDLER_TYPE.DATA
icon_path = "icon.png"

__all__ = [
    "Handler",
    "version",
    "name",
    "type",
    "title",
    "description",
    "import_error",
    "icon_path",
]
