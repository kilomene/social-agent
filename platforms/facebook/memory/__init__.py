""" Facebook memory: a namespaced VIEW into the shared memory DB.

No separate database lives here — every call delegates to ``core.memory``
with the platform preset. (The no-duplication tripwire asserts this
directory never contains a ``.db`` file.)
"""

from core.memory import PlatformMemoryView

PLATFORM = "facebook"


def view(home):
    """Return the Facebook-scoped view of the shared memory DB."""
    return PlatformMemoryView(home, PLATFORM)
