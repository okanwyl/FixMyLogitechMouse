from ctypes import *
from ctypes.wintypes import *
import pystray
from pystray import MenuItem as item, Menu as menu


from PIL import Image, ImageDraw


user32 = WinDLL("user32", use_last_error=True)

HC_ACTION = 0
WH_MOUSE_LL = 14

WM_QUIT = 0x0012
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
WM_MOUSEWHEEL = 0x020A
WM_MOUSEHWHEEL = 0x020E

last_click_time = 0
click_threshold = 90

MSG_TEXT = {
    WM_MOUSEMOVE: "WM_MOUSEMOVE",
    WM_LBUTTONDOWN: "WM_LBUTTONDOWN",
    WM_LBUTTONUP: "WM_LBUTTONUP",
    WM_RBUTTONDOWN: "WM_RBUTTONDOWN",
    WM_RBUTTONUP: "WM_RBUTTONUP",
    WM_MBUTTONDOWN: "WM_MBUTTONDOWN",
    WM_MBUTTONUP: "WM_MBUTTONUP",
    WM_MOUSEWHEEL: "WM_MOUSEWHEEL",
    WM_MOUSEHWHEEL: "WM_MOUSEHWHEEL",
}

ULONG_PTR = WPARAM
LRESULT = LPARAM
LPMSG = POINTER(MSG)

HOOKPROC = WINFUNCTYPE(LRESULT, c_int, WPARAM, LPARAM)
LowLevelMouseProc = HOOKPROC


class MSLLHOOKSTRUCT(Structure):
    _fields_ = (
        ("pt", POINT),
        ("mouseData", DWORD),
        ("flags", DWORD),
        ("time", DWORD),
        ("dwExtraInfo", ULONG_PTR),
    )


LPMSLLHOOKSTRUCT = POINTER(MSLLHOOKSTRUCT)


def errcheck_bool(result, func, args):
    if not result:
        raise WinError(get_last_error())
    return args


user32.SetWindowsHookExW.errcheck = errcheck_bool
user32.SetWindowsHookExW.restype = HHOOK
user32.SetWindowsHookExW.argtypes = (
    c_int,  # _In_ idHook
    HOOKPROC,  # _In_ lpfn
    HINSTANCE,  # _In_ hMod
    DWORD,
)  # _In_ dwThreadId

user32.CallNextHookEx.restype = LRESULT
user32.CallNextHookEx.argtypes = (
    HHOOK,  # _In_opt_ hhk
    c_int,  # _In_     nCode
    WPARAM,  # _In_     wParam
    LPARAM,
)  # _In_     lParam

user32.GetMessageW.argtypes = (
    LPMSG,  # _Out_    lpMsg
    HWND,  # _In_opt_ hWnd
    UINT,  # _In_     wMsgFilterMin
    UINT,
)  # _In_     wMsgFilterMax

user32.TranslateMessage.argtypes = (LPMSG,)
user32.DispatchMessageW.argtypes = (LPMSG,)


@LowLevelMouseProc
def LLMouseProc(nCode, wParam, lParam):
    global last_click_time
    msg = cast(lParam, LPMSLLHOOKSTRUCT)[0]
    if nCode == HC_ACTION:
        if wParam == WM_LBUTTONDOWN:
            current_time = time.time() * 1000
            if current_time - last_click_time < click_threshold:
                # Fuck off logitech
                return 1
            last_click_time = current_time
    return user32.CallNextHookEx(None, nCode, wParam, lParam)


def mouse_msg_loop():
    hHook = user32.SetWindowsHookExW(WH_MOUSE_LL, LLMouseProc, None, 0)
    msg = MSG()
    while True:
        bRet = user32.GetMessageW(byref(msg), None, 0, 0)
        if not bRet:
            break
        if bRet == -1:
            raise WinError(get_last_error())
        user32.TranslateMessage(byref(msg))
        user32.DispatchMessageW(byref(msg))


def create_image(width, height, color1, color2):
    # Generate an image and draw a pattern
    image = Image.new("RGB", (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
    dc.rectangle((0, height // 2, width // 2, height), fill=color2)

    return image


def on_exit(icon, item):
    user32.PostThreadMessageW(t.ident, WM_QUIT, 0, 0)
    icon.stop()


if __name__ == "__main__":
    import time
    import threading

    t = threading.Thread(target=mouse_msg_loop)
    t.start()

    icon = pystray.Icon(
        "FixMyLogitechMouse",
        icon=create_image(64, 64, "black", "white"),
        menu=menu(
            item("FixMyLogitechMouse", lambda icon, item: print("empty")),
            item("Exit", lambda icon, item: on_exit(icon, item)),
        ),
    )

    icon.run()
