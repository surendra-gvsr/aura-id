# agent/src/pairing.py
import tkinter as tk
from tkinter import messagebox
import keyring
import requests
import structlog

log = structlog.get_logger()

_KEYRING_SERVICE = "AuraID-Agent"
_KEYRING_KEY = "workstation_token"


class PairingError(Exception):
    pass


class PairingClient:
    def __init__(self, api_base: str) -> None:
        self._api_base = api_base.rstrip("/")

    def claim(self, pairing_code: str) -> str:
        """POST /workstations/claim — returns workstation token."""
        try:
            r = requests.post(
                f"{self._api_base}/workstations/claim",
                json={"pairing_code": pairing_code},
                timeout=(5, 10),
            )
        except requests.RequestException as exc:
            raise PairingError(f"network error: {exc}") from exc
        if not r.ok:
            body = {}
            if r.headers.get("content-type", "").startswith("application/json"):
                body = r.json()
            raise PairingError(body.get("error", f"http_{r.status_code}"))
        return r.json()["token"]


def save_token(token: str) -> None:
    keyring.set_password(_KEYRING_SERVICE, _KEYRING_KEY, token)


def load_token() -> str | None:
    return keyring.get_password(_KEYRING_SERVICE, _KEYRING_KEY)


def delete_token() -> None:
    try:
        keyring.delete_password(_KEYRING_SERVICE, _KEYRING_KEY)
    except keyring.errors.PasswordDeleteError:
        pass


def run_pairing_dialog(api_base: str) -> str | None:
    """Show tkinter pairing dialog. Returns token on success, None on cancel."""
    root = tk.Tk()
    root.title("Aura ID — Pair Workstation")
    root.geometry("420x180")
    root.resizable(False, False)

    tk.Label(root, text="Enter pairing code from your Aura ID dashboard:").pack(pady=(20, 5))
    code_var = tk.StringVar()
    entry = tk.Entry(root, textvariable=code_var, width=32, font=("Arial", 13))
    entry.pack(pady=5)
    entry.focus_set()

    result: list[str | None] = [None]

    def _pair() -> None:
        code = code_var.get().strip().upper()
        if not code:
            messagebox.showerror("Error", "Please enter a pairing code.")
            return
        try:
            token = PairingClient(api_base).claim(code)
            save_token(token)
            result[0] = token
            log.info("pairing.success")
            root.destroy()
        except PairingError as exc:
            messagebox.showerror("Pairing failed", str(exc))

    frame = tk.Frame(root)
    frame.pack(pady=14)
    tk.Button(frame, text="Pair", command=_pair, width=12).pack(side=tk.LEFT, padx=5)
    tk.Button(frame, text="Cancel", command=root.destroy, width=12).pack(side=tk.LEFT, padx=5)
    root.bind("<Return>", lambda _: _pair())
    root.mainloop()
    return result[0]
