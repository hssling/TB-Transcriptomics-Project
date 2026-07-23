"""Import-time shim: bypass the Windows WMI probe used by platform.uname().

On this host the WMI provider does not respond, so platform._wmi_query blocks
indefinitely. scikit-learn calls platform.machine() while importing
sklearn.utils.fixes, which stalls every downstream import. Seeding the uname
cache from sys.getwindowsversion() and disabling the WMI path keeps
platform.* fully functional without touching the interpreter installation.

Import this module before scikit-learn in any script that needs it.
"""
import platform
import sys


def _apply():
    if not sys.platform.startswith("win"):
        return
    if getattr(platform, "_wmi_query", None) is not None:
        def _blocked(*_args, **_kwargs):
            raise OSError("WMI disabled by env_fix")
        platform._wmi_query = _blocked
    if getattr(platform, "_uname_cache", None) is None:
        wv = sys.getwindowsversion()
        release = {10: "10"}.get(wv.major, str(wv.major))
        version = f"{wv.major}.{wv.minor}.{wv.build}"
        machine = __import__("os").environ.get("PROCESSOR_ARCHITECTURE", "AMD64")
        platform._uname_cache = platform.uname_result(
            system="Windows",
            node=__import__("os").environ.get("COMPUTERNAME", "localhost"),
            release=release,
            version=version,
            machine=machine,
        )


_apply()
