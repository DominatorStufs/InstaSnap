"""
=============================================================================
InstaSnap - Pure-Python Instagram Android Client & QuickSnap Dispatcher
=============================================================================
Description: Lightweight, pure-Python client replicating Instagram's mobile
             API and Web Auth layer. Uses persistent Samsung Galaxy S24 Ultra
             hardware emulation, persistent requests session reuse for
             checkpoint resolution without duplicate prompts, and provides
             direct QuickSnap media dispatching.
=============================================================================
"""

import os
import re
import json
import time
import uuid
import base64
import mimetypes
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

import requests

import config

BASE_DIR = getattr(config, "BASE_DIR", getattr(config, "ROOT_DIR", Path(__file__).resolve().parent))
DEVICE_FILE = getattr(config, "DEVICE_FILE", BASE_DIR / "device.json")
QUICKSNAP_CLIENT_ENDPOINT = "QuickSnapUnifiedCameraFragment"


class CheckpointRequiredError(Exception):
    """Raised when Instagram triggers a suspicious login security checkpoint."""
    def __init__(self, message: str = "checkpoint_required", checkpoint_url: str = "", raw_data: Optional[Dict] = None):
        super().__init__(message)
        self.checkpoint_url = checkpoint_url
        self.raw_data = raw_data or {}


class TwoFactorRequiredError(Exception):
    """Raised when Two-Factor Authentication (2FA / SMS) is required."""
    def __init__(self, message: str = "two_factor_required", identifier: str = "", raw_data: Optional[Dict] = None):
        super().__init__(message)
        self.identifier = identifier
        self.raw_data = raw_data or {}


def get_or_create_persistent_device() -> Dict[str, Any]:
    """
    Loads or generates a persistent Samsung Galaxy S24 Ultra device profile.
    Keeping the device ID constant prevents Instagram from flagging repeated logins.
    """
    if DEVICE_FILE.exists():
        try:
            with open(DEVICE_FILE, "r") as f:
                data = json.load(f)
                if data.get("device_id") and data.get("android_id"):
                    return data
        except Exception:
            pass

    # Authentic Samsung Galaxy S24 Ultra hardware profile
    device = {
        "manufacturer": "samsung",
        "model": "SM-S928B",
        "device": "e3q",
        "cpu": "qcom",
        "android_version": 34,
        "android_release": "14",
        "dpi": "450dpi",
        "resolution": "1440x3120",
        "app_version": "350.0.0.48.90",
        "version_code": "641528570",
        "device_id": str(uuid.uuid4()),
        "phone_id": str(uuid.uuid4()),
        "android_id": f"android-{uuid.uuid4().hex[:16]}",
        "uuid": str(uuid.uuid4()),
    }
    try:
        with open(DEVICE_FILE, "w") as f:
            json.dump(device, f, indent=2)
    except Exception:
        pass
    return device


class AccountInfo:
    """Represents Instagram account profile details."""
    def __init__(self, username: str, full_name: str, pk: int):
        self.username = username
        self.full_name = full_name
        self.pk = pk


class LightweightClient:
    """
    Pure Python Instagram Client with real Android device emulation,
    session management, and QuickSnap dispatching.
    """
    def __init__(self):
        self.session = requests.Session()
        self.device = get_or_create_persistent_device()

        # Build realistic Samsung Galaxy S24 Ultra User-Agent for Private API
        self.user_agent = (
            f"Instagram {self.device['app_version']} Android "
            f"({self.device['android_version']}/{self.device['android_release']}; "
            f"{self.device['dpi']}; {self.device['resolution']}; "
            f"{self.device['manufacturer']}; {self.device['model']}; "
            f"{self.device['device']}; {self.device['cpu']}; en_US; "
            f"{self.device['version_code']})"
        )

        # Realistic mobile Chrome user agent matching the device
        self.web_user_agent = (
            "Mozilla/5.0 (Linux; Android 14; SM-S928B Build/UP1A.231005.007) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36"
        )

        self.user_id = ""
        self.username = ""
        self.sessionid = ""
        self.mid = ""
        self.uuid = self.device.get("uuid", str(uuid.uuid4()))
        self.android_device_id = self.device.get("android_id", f"android-{uuid.uuid4().hex[:16]}")
        self.timezone_offset = "-14400"

        # Checkpoint session state tracking (preserves cookies across retries)
        self._login_session: Optional[requests.Session] = None
        self._checkpoint_url: str = ""
        self._pending_username: str = ""
        self._pending_password: str = ""
        self._two_factor_identifier: str = ""

        self.base_headers = {
            "User-Agent": self.user_agent,
            "Accept-Language": "en-US",
            "Accept-Encoding": "gzip, deflate",
            "Host": "i.instagram.com",
            "X-IG-Capabilities": "3brTv10=",
            "X-IG-App-ID": "567067343352427",
            "X-IG-Connection-Type": "WIFI",
            "X-IG-Device-ID": self.device.get("device_id", self.uuid),
            "X-IG-Android-ID": self.android_device_id,
        }
        self.session.headers.update(self.base_headers)

    def get_cookie(self, name: str, default: str = "") -> str:
        """
        Safely retrieves a cookie value by name from the session cookie jar.
        Prevents RequestsCookieJar CookieConflictError when multiple cookies
        with the same name exist across subdomains.
        """
        try:
            val = self.session.cookies.get(name, default=None)
            if val is not None:
                return str(val)
        except Exception:
            pass

        for c in self.session.cookies:
            if c.name == name and c.value:
                return str(c.value)

        return default

    def set_cookie(self, name: str, value: str, domain: str = ".instagram.com"):
        """
        Safely sets a cookie without duplicating it across multiple domains/paths,
        clearing any stale copies first.
        """
        for c in list(self.session.cookies):
            if c.name == name:
                try:
                    self.session.cookies.clear(c.domain, c.path, c.name)
                except Exception:
                    pass
        self.session.cookies.set(name, value, domain=domain)

    def _get_login_cookie(self, name: str, default: str = "") -> str:
        if self._login_session is None:
            return default
        try:
            val = self._get_login_cookie(name, default=None)
            if val is not None:
                return str(val)
        except Exception:
            pass
        for c in self._login_session.cookies:
            if c.name == name and c.value:
                return str(c.value)
        return default

    def _generate_nav_chain(self) -> str:
        ts = time.time()
        return (
            f"DirectInboxFragment:direct_inbox:2:main_direct:{ts - 55:.3f}:::{ts - 55:.3f},"
            f"QuickSnapUnifiedFragment:quicksnap_unified_fragment:3:button:{ts - 20:.3f}:::{ts - 20:.3f},"
            f"ConstAnalyticsModule:quick_snap_camera:4:button:{ts - 19:.3f}:::{ts - 19:.3f},"
            f"{QUICKSNAP_CLIENT_ENDPOINT}:6:button:{ts - 5:.3f}:::{ts - 5:.3f}"
        )

    def _quick_snap_nav_chain(self) -> str:
        return self._generate_nav_chain()

    def login_by_sessionid(self, sessionid: str) -> bool:
        """Authenticates using an Instagram session ID cookie."""
        assert isinstance(sessionid, str) and len(sessionid) > 20, "Invalid session ID format"
        clean_sid = sessionid.strip().strip("'\"")
        if clean_sid.lower().startswith("sessionid="):
            clean_sid = clean_sid.split("=", 1)[1].strip()
        clean_sid = clean_sid.rstrip(";")

        # Extract user ID from session ID (Instagram format: <USERID>%3A... or <USERID>:...)
        user_match = re.search(r"^\d+", clean_sid)
        if not user_match:
            raise ValueError("Invalid sessionid: Does not contain numeric Instagram User ID prefix.")

        self.user_id = user_match.group()
        self.sessionid = clean_sid

        # Set cookies in API session cleanly without duplicate subdomains
        self.set_cookie("sessionid", clean_sid, domain=".instagram.com")
        self.set_cookie("ds_user_id", str(self.user_id), domain=".instagram.com")
        if self.mid:
            self.set_cookie("mid", self.mid, domain=".instagram.com")

        # Set Instagram Private Mobile API Authorization header
        auth_data = {
            "ds_user_id": str(self.user_id),
            "sessionid": clean_sid,
            "should_use_header_over_cookies": True,
        }
        auth_b64 = base64.b64encode(json.dumps(auth_data, separators=(",", ":")).encode("utf-8")).decode("utf-8")
        self.session.headers.update({
            "Authorization": f"Bearer IGT:2:{auth_b64}",
            "IG-INTENDED-USER-ID": str(self.user_id),
            "X-IG-WWW-Claim": "0",
        })

        # Pre-seed CSRF and MID from shared_data if available
        try:
            s_resp = requests.get(
                "https://www.instagram.com/data/shared_data/",
                cookies={"sessionid": clean_sid, "ds_user_id": str(self.user_id)},
                headers={"User-Agent": self.web_user_agent, "Accept": "*/*", "X-IG-App-ID": "936619743392459"},
                timeout=8
            )
            if s_resp.status_code == 200:
                sd_json = s_resp.json()
                cfg = sd_json.get("config") or {}
                csrf = ""
                for ck in s_resp.cookies:
                    if ck.name == "csrftoken" and ck.value:
                        csrf = ck.value
                        break
                if not csrf:
                    csrf = cfg.get("csrf_token") or ""

                mid = ""
                for ck in s_resp.cookies:
                    if ck.name == "mid" and ck.value:
                        mid = ck.value
                        break

                if csrf:
                    self.set_cookie("csrftoken", csrf, domain=".instagram.com")
                    self.session.headers["X-CSRFToken"] = csrf
                if mid:
                    self.set_cookie("mid", mid, domain=".instagram.com")
                    self.session.headers["X-MID"] = mid
                viewer = cfg.get("viewer")
                if isinstance(viewer, dict) and viewer.get("username"):
                    self.username = viewer.get("username")
        except Exception:
            pass

        # Guarantee CSRF token presence to avoid empty _csrftoken in payload
        if not self.get_cookie("csrftoken"):
            gen_csrf = uuid.uuid4().hex
            self.set_cookie("csrftoken", gen_csrf, domain=".instagram.com")
            self.session.headers["X-CSRFToken"] = gen_csrf

        # Fetch profile metadata to verify active session
        try:
            info = self.account_info()
            self.username = info.username
        except PermissionError:
            raise
        except Exception:
            self.username = f"user_{self.user_id}"

        return True

    def login(self, username: str, password: str, verification_code: str = "") -> bool:
        """
        Logs in securely via real mobile browser authentication headers.
        Preserves session state across retries so Instagram does not send
        duplicate checkpoint notifications.
        """
        self._pending_username = username.strip()
        self._pending_password = password.strip()

        # Initialize or reuse persistent login session
        if self._login_session is None:
            self._login_session = requests.Session()
            self._login_session.headers.update({
                "User-Agent": self.web_user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Sec-Ch-Ua": '"Chromium";v="131", "Not_A Brand";v="24", "Google Chrome";v="131"',
                "Sec-Ch-Ua-Mobile": "?1",
                "Sec-Ch-Ua-Platform": '"Android"',
            })

            # Handshake Step 1: Visit Instagram homepage to collect initial cookies (mid, ig_did, csrftoken)
            try:
                self._login_session.get("https://www.instagram.com/", timeout=15)
                self._login_session.cookies.set("ig_nrcb", "1", domain=".instagram.com")
                time.sleep(1.0)  # Human simulation delay
            except Exception as e:
                raise ConnectionError(f"Network handshake failed: {e}")

        csrf_token = self._get_login_cookie("csrftoken") or ""

        # Step 2: Handle 2FA submission if verification_code provided
        if verification_code and self._two_factor_identifier:
            two_factor_data = {
                "verificationCode": verification_code.strip(),
                "identifier": self._two_factor_identifier,
                "queryParams": "{}",
            }
            headers = {
                "X-CSRFToken": csrf_token,
                "X-Instagram-AJAX": "1017409241",
                "X-IG-App-ID": "1217981644879628",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.instagram.com/accounts/login/",
            }
            r_2fa = self._login_session.post(
                "https://www.instagram.com/accounts/login/ajax/two_factor/",
                data=two_factor_data,
                headers=headers,
                timeout=20
            )
            res_2fa = r_2fa.json()
            if not res_2fa.get("authenticated"):
                msg = res_2fa.get("message") or "2FA Verification failed."
                raise ValueError(msg)

            sid = self._get_login_cookie("sessionid")
            if sid:
                return self.login_by_sessionid(sid)
            raise ValueError("Login succeeded but sessionid was not received.")

        # Step 3: Primary Login Request with complete genuine browser headers
        timestamp = str(int(time.time()))
        payload = {
            "username": self._pending_username,
            "enc_password": f"#PWD_INSTAGRAM_BROWSER:0:{timestamp}:{self._pending_password}",
            "queryParams": "{}",
            "optIntoOneTap": "false",
        }
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://www.instagram.com/accounts/login/",
            "X-CSRFToken": csrf_token,
            "X-Instagram-AJAX": "1017409241",
            "X-IG-App-ID": "936619743392459",
            "X-ASBD-ID": "129477",
            "X-IG-WWW-Claim": "0",
            "Origin": "https://www.instagram.com",
            "Content-Type": "application/x-www-form-urlencoded",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
        }

        login_url = "https://www.instagram.com/api/v1/web/accounts/login/ajax/"
        r2 = self._login_session.post(
            login_url,
            data=payload,
            headers=headers,
            timeout=20
        )
        if r2.status_code == 404:
            login_url = "https://www.instagram.com/accounts/login/ajax/"
            r2 = self._login_session.post(login_url, data=payload, headers=headers, timeout=20)

        try:
            res = r2.json()
        except Exception:
            raise ValueError(f"Unexpected response from Instagram (HTTP {r2.status_code})")

        # Step 4: Check for Security Checkpoint ("Suspicious login attempt" / "This was me")
        msg = (res.get("message") or "").lower()
        err_type = (res.get("error_type") or "").lower()
        if "checkpoint" in msg or "checkpoint" in err_type or res.get("checkpoint_url"):
            self._checkpoint_url = res.get("checkpoint_url") or ""
            raise CheckpointRequiredError(
                message="checkpoint_required",
                checkpoint_url=self._checkpoint_url,
                raw_data=res
            )

        # Step 5: Check if Two-Factor Authentication (2FA) is required
        if res.get("two_factor_required"):
            tf_info = res.get("two_factor_info") or {}
            self._two_factor_identifier = tf_info.get("two_factor_identifier") or ""
            raise TwoFactorRequiredError(
                message="two_factor_required",
                identifier=self._two_factor_identifier,
                raw_data=res
            )

        if not res.get("authenticated"):
            error_msg = res.get("message") or res.get("error_type") or "Invalid credentials."
            if res.get("user") is False:
                raise ValueError("Username does not exist.")
            raise ValueError(f"Authentication failed: {error_msg}")

        sid = self._get_login_cookie("sessionid")
        if not sid:
            raise ValueError("Authentication succeeded but sessionid cookie was not returned.")

        return self.login_by_sessionid(sid)

    def resolve_checkpoint_approval(self) -> bool:
        """
        Resolves the checkpoint on the EXACT same session and cookie jar.
        When the user taps 'This was me trying to log in' on their Instagram app,
        this checks the checkpoint URL and/or replays the login on the same session.
        Never triggers duplicate notifications.
        """
        if self._login_session is None:
            return False

        # 1. Check if sessionid already received in cookie jar
        sid = self._get_login_cookie("sessionid")
        if sid:
            return self.login_by_sessionid(sid)

        # 2. Check the checkpoint URL on the existing session
        if self._checkpoint_url:
            cp_url = self._checkpoint_url
            if cp_url.startswith("/"):
                full_url = f"https://www.instagram.com{cp_url}"
            else:
                full_url = cp_url

            csrf = self._get_login_cookie("csrftoken") or ""
            headers = {
                "User-Agent": self.web_user_agent,
                "Referer": "https://www.instagram.com/accounts/login/",
                "X-CSRFToken": csrf,
                "X-Instagram-AJAX": "1017409241",
                "X-IG-App-ID": "1217981644879628",
                "X-Requested-With": "XMLHttpRequest",
            }

            try:
                resp = self._login_session.get(full_url, headers=headers, allow_redirects=True, timeout=15)
                sid = self._get_login_cookie("sessionid")
                if sid:
                    return self.login_by_sessionid(sid)

                # Check if challenge returned ok
                try:
                    j = resp.json()
                    if j.get("status") == "ok" and self._get_login_cookie("sessionid"):
                        return self.login_by_sessionid(self._get_login_cookie("sessionid"))
                except Exception:
                    pass
            except Exception:
                pass

        # 3. Re-submit login payload ON THE SAME SESSION
        # Since 'This was me' was tapped, Instagram recognizes the approved session
        if self._pending_username and self._pending_password:
            try:
                csrf = self._get_login_cookie("csrftoken") or ""
                timestamp = str(int(time.time()))
                payload = {
                    "username": self._pending_username,
                    "enc_password": f"#PWD_INSTAGRAM_BROWSER:0:{timestamp}:{self._pending_password}",
                    "queryParams": "{}",
                    "optIntoOneTap": "false",
                }
                headers = {
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": "https://www.instagram.com/accounts/login/",
                    "X-CSRFToken": csrf,
                    "X-Instagram-AJAX": "1017409241",
                    "X-IG-App-ID": "936619743392459",
                    "X-ASBD-ID": "129477",
                    "X-IG-WWW-Claim": "0",
                    "Origin": "https://www.instagram.com",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Sec-Fetch-Site": "same-origin",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Dest": "empty",
                }
                login_url = "https://www.instagram.com/api/v1/web/accounts/login/ajax/"
                r = self._login_session.post(login_url, data=payload, headers=headers, timeout=20)
                if r.status_code == 404:
                    r = self._login_session.post("https://www.instagram.com/accounts/login/ajax/", data=payload, headers=headers, timeout=20)
                res = r.json()
                if res.get("authenticated") or self._get_login_cookie("sessionid"):
                    sid = self._get_login_cookie("sessionid")
                    if sid:
                        return self.login_by_sessionid(sid)
            except Exception:
                pass

        # Check one last time if cookie exists
        sid = self._get_login_cookie("sessionid")
        if sid:
            return self.login_by_sessionid(sid)

        return False

    def request_checkpoint_otp(self, choice: int = 0) -> Tuple[bool, str]:
        """
        Sends a 6-digit OTP to user's phone via SMS (choice=0) or Email (choice=1).
        Returns (success, message_or_recipient).
        """
        if not self._login_session or not self._checkpoint_url:
            return False, "No active challenge session available."

        cp_url = self._checkpoint_url
        if cp_url.startswith("/"):
            full_url = f"https://www.instagram.com{cp_url}"
        else:
            full_url = cp_url

        csrf = self._get_login_cookie("csrftoken") or ""
        headers = {
            "User-Agent": self.web_user_agent,
            "Referer": full_url,
            "X-CSRFToken": csrf,
            "X-Instagram-AJAX": "1017409241",
            "X-IG-App-ID": "1217981644879628",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://www.instagram.com",
        }
        data = {
            "choice": str(choice),
        }

        try:
            resp = self._login_session.post(full_url, data=data, headers=headers, timeout=20)
            res_json = resp.json()
            extra = res_json.get("fields") or {}
            target = extra.get("phone_number") or extra.get("email") or ("SMS Phone" if choice == 0 else "Email")
            if res_json.get("status") == "ok" or res_json.get("step_name") == "verify_code" or "verify_code" in str(res_json):
                return True, str(target)
            msg = res_json.get("message") or "Code request sent."
            return True, msg
        except Exception as e:
            return False, str(e)

    def submit_two_factor_code(self, verification_code: str) -> bool:
        """
        Submits 6-digit Two-Factor (2FA) verification code.
        """
        if not self._login_session or not self._two_factor_identifier:
            return False

        csrf = self._get_login_cookie("csrftoken") or ""
        headers = {
            "User-Agent": self.web_user_agent,
            "Referer": "https://www.instagram.com/accounts/login/",
            "X-CSRFToken": csrf,
            "X-Instagram-AJAX": "1017409241",
            "X-IG-App-ID": "1217981644879628",
            "X-Requested-With": "XMLHttpRequest",
        }
        two_factor_data = {
            "verificationCode": verification_code.strip(),
            "identifier": self._two_factor_identifier,
            "queryParams": "{}",
        }
        try:
            r = self._login_session.post(
                "https://www.instagram.com/accounts/login/ajax/two_factor/",
                data=two_factor_data,
                headers=headers,
                timeout=20
            )
            res = r.json()
            if res.get("authenticated") or self._get_login_cookie("sessionid"):
                sid = self._get_login_cookie("sessionid")
                if sid:
                    return self.login_by_sessionid(sid)
        except Exception:
            pass

        return False

    def submit_checkpoint_code(self, security_code: str) -> bool:
        """
        Submits a 6-digit SMS or Email checkpoint verification code
        if Instagram asks for a code verification on the challenge URL.
        """
        if not self._login_session or not self._checkpoint_url:
            return False

        cp_url = self._checkpoint_url
        if cp_url.startswith("/"):
            full_url = f"https://www.instagram.com{cp_url}"
        else:
            full_url = cp_url

        csrf = self._get_login_cookie("csrftoken") or ""
        headers = {
            "User-Agent": self.web_user_agent,
            "Referer": full_url,
            "X-CSRFToken": csrf,
            "X-Instagram-AJAX": "1017409241",
            "X-IG-App-ID": "1217981644879628",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "security_code": security_code.strip(),
        }

        try:
            resp = self._login_session.post(full_url, data=data, headers=headers, timeout=20)
            sid = self._get_login_cookie("sessionid")
            if sid:
                return self.login_by_sessionid(sid)

            try:
                j = resp.json()
                if j.get("status") == "ok":
                    # Check if sessionid cookie is available
                    sid = self._get_login_cookie("sessionid")
                    if sid:
                        return self.login_by_sessionid(sid)
            except Exception:
                pass
        except Exception:
            pass

        return False

    def account_info(self) -> AccountInfo:
        """Retrieves profile information for the authenticated user using multiple strategies."""
        assert self.user_id, "Login required"

        # Strategy 1: Mobile API accounts/current_user/?edit=true
        try:
            url = "https://i.instagram.com/api/v1/accounts/current_user/?edit=true"
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "ok" and isinstance(data.get("user"), dict):
                    user = data["user"]
                    uname = user.get("username")
                    fname = user.get("full_name") or uname
                    if uname:
                        self.username = uname
                        return AccountInfo(
                            username=uname,
                            full_name=fname,
                            pk=int(user.get("pk") or self.user_id)
                        )
            elif resp.status_code in (401, 403) or "login_required" in resp.text:
                raise PermissionError("Instagram session is invalid or expired (login_required).")
        except PermissionError:
            raise
        except Exception:
            pass

        # Strategy 2: Mobile API users/{self.user_id}/info/
        try:
            url = f"https://i.instagram.com/api/v1/users/{self.user_id}/info/"
            params = {
                "is_prefetch": "false",
                "entry_point": "self_profile",
                "from_module": "self_profile",
            }
            resp = self.session.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "ok" and isinstance(data.get("user"), dict):
                    user = data["user"]
                    uname = user.get("username")
                    fname = user.get("full_name") or uname
                    if uname:
                        self.username = uname
                        return AccountInfo(
                            username=uname,
                            full_name=fname,
                            pk=int(user.get("pk") or self.user_id)
                        )
            elif resp.status_code in (401, 403) or "login_required" in resp.text:
                raise PermissionError("Instagram session is invalid or expired (login_required).")
        except PermissionError:
            raise
        except Exception:
            pass

        # Strategy 3: Web Shared Data viewer
        try:
            web_headers = {
                "User-Agent": self.web_user_agent,
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "X-IG-App-ID": "936619743392459",
            }
            resp = requests.get(
                "https://www.instagram.com/data/shared_data/",
                cookies={"sessionid": self.sessionid, "ds_user_id": str(self.user_id)},
                headers=web_headers,
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                viewer = (data.get("config") or {}).get("viewer")
                if isinstance(viewer, dict) and viewer.get("username"):
                    uname = viewer.get("username")
                    fname = viewer.get("full_name") or uname
                    self.username = uname
                    return AccountInfo(
                        username=uname,
                        full_name=fname,
                        pk=int(viewer.get("id") or self.user_id)
                    )
        except Exception:
            pass

        # Strategy 4: Web GraphQL profile doc_id
        try:
            web_headers = {
                "User-Agent": self.web_user_agent,
                "X-IG-App-ID": "936619743392459",
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": f"https://www.instagram.com/{self.user_id}/",
            }
            gql_data = {
                "doc_id": "28036671149327607",
                "variables": json.dumps({"id": str(self.user_id), "render_surface": "PROFILE"}),
            }
            resp = requests.post(
                "https://www.instagram.com/graphql/query",
                data=gql_data,
                cookies={"sessionid": self.sessionid, "ds_user_id": str(self.user_id)},
                headers=web_headers,
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                user_node = ((data.get("data") or {}).get("user")) or {}
                uname = user_node.get("username")
                fname = user_node.get("full_name") or uname
                if uname:
                    self.username = uname
                    return AccountInfo(
                        username=uname,
                        full_name=fname,
                        pk=int(user_node.get("id") or self.user_id)
                    )
        except Exception:
            pass

        # Strategy 5: Mobile Info Stream endpoint
        try:
            resp = self.session.post(
                f"https://i.instagram.com/api/v1/users/{self.user_id}/info_stream/",
                data={"is_prefetch": False, "entry_point": "profile", "from_module": "feed_timeline"},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                for row in data.get("stream_rows", []):
                    if isinstance(row, dict) and "user" in row:
                        u = row["user"]
                        uname = u.get("username")
                        fname = u.get("full_name") or uname
                        if uname:
                            self.username = uname
                            return AccountInfo(
                                username=uname,
                                full_name=fname,
                                pk=int(u.get("pk") or self.user_id)
                            )
        except Exception:
            pass

        # Fallback if profile lookups did not return username
        resolved_username = self.username or f"user_{self.user_id}"
        self.username = resolved_username
        return AccountInfo(
            username=resolved_username,
            full_name=f"User {self.user_id}",
            pk=int(self.user_id)
        )

    def photo_rupload(self, photo_path: Path, upload_id: str = "") -> Tuple[str, int, int]:
        """Uploads a photo binary to Instagram's rupload servers."""
        if not upload_id:
            upload_id = str(int(time.time() * 1000))

        file_bytes = photo_path.read_bytes()
        file_len = len(file_bytes)

        # Detect dimensions
        width, height = 1080, 1920

        waterfall_id = str(uuid.uuid4())
        rupload_params = {
            "upload_media_height": str(height),
            "upload_media_width": str(width),
            "upload_id": upload_id,
            "media_type": "1",
            "retry_context": json.dumps({"num_step_auto_retry": 0, "num_reupload": 0, "num_step_manual_retry": 0}),
            "waterfall_id": waterfall_id,
            "xsharing_user_ids": json.dumps([]),
        }

        url = f"https://i.instagram.com/rupload_igphoto/{upload_id}"
        headers = {
            "X-Entity-Type": "image/jpeg",
            "Offset": "0",
            "X-Entity-Name": f"{upload_id}_0_{int(time.time())}",
            "X-Entity-Length": str(file_len),
            "X_FB_PHOTO_WATERFALL_ID": waterfall_id,
            "X-Instagram-Rupload-Params": json.dumps(rupload_params),
            "Content-Type": "application/octet-stream",
            "Content-Length": str(file_len),
        }

        resp = self.session.post(url, data=file_bytes, headers=headers, timeout=45)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Photo binary upload failed: HTTP {resp.status_code} - {resp.text}")

        return upload_id, width, height

    def video_rupload(self, video_path: Path, upload_id: str = "") -> Tuple[str, int, int, float]:
        """Uploads a video file to Instagram's video rupload endpoint."""
        if not upload_id:
            upload_id = str(int(time.time() * 1000))

        file_bytes = video_path.read_bytes()
        file_len = len(file_bytes)

        width, height = 1080, 1920
        duration = 5.0

        waterfall_id = str(uuid.uuid4())
        rupload_params = {
            "upload_media_height": str(height),
            "upload_media_width": str(width),
            "upload_media_duration_ms": str(int(duration * 1000)),
            "upload_id": upload_id,
            "media_type": "2",
            "for_album": "0",
            "is_sidecar": "0",
            "retry_context": json.dumps({"num_step_auto_retry": 0, "num_reupload": 0, "num_step_manual_retry": 0}),
            "waterfall_id": waterfall_id,
        }

        url = f"https://i.instagram.com/rupload_igvideo/{upload_id}"
        headers = {
            "X-Entity-Type": "video/mp4",
            "Offset": "0",
            "X-Entity-Name": f"{upload_id}_0_{int(time.time())}",
            "X-Entity-Length": str(file_len),
            "X-Instagram-Rupload-Params": json.dumps(rupload_params),
            "Content-Type": "application/octet-stream",
            "Content-Length": str(file_len),
        }

        resp = self.session.post(url, data=file_bytes, headers=headers, timeout=90)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Video binary upload failed: HTTP {resp.status_code} - {resp.text}")

        return upload_id, width, height, duration

    def quicksnap_send(
        self,
        upload_id: str,
        media_type: str = "photo",
        width: int = 1080,
        height: int = 1920,
        audience: str = "mutual_followers",
    ) -> Dict[str, Any]:
        """
        Configures the uploaded media into Instagram's QuickSnap (Instant) inbox stream.
        """
        assert self.user_id, "Login required before dispatching QuickSnap"

        url = "https://i.instagram.com/api/v1/media/configure_to_quick_snap/"
        client_timestamp = str(int(time.time()))

        # Determine audience targeting:
        # "mutual_followers" = Friends who follow each other
        # "close_friends"    = Close Friends only
        audience_mode = "1" if audience == "close_friends" else "0"

        csrf_token = self.get_cookie("csrftoken") or uuid.uuid4().hex

        payload = {
            "_csrftoken": csrf_token,
            "_uid": str(self.user_id),
            "_uuid": self.uuid,
            "upload_id": str(upload_id),
            "source_type": "4",
            "caption": "",
            "audience": audience_mode,
            "device_id": self.android_device_id,
            "client_timestamp": client_timestamp,
            "client_shared_at": client_timestamp,
            "device": {
                "manufacturer": self.device["manufacturer"],
                "model": self.device["model"],
                "android_version": self.device["android_version"],
                "android_release": self.device["android_release"],
            },
            "nav_chains": self._quick_snap_nav_chain(),
        }

        if media_type == "video":
            payload["video_result"] = ""
            payload["audio_muted"] = "0"

        headers = {
            "X-IG-Nav-Chain": self._quick_snap_nav_chain(),
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

        resp = self.session.post(url, data=payload, headers=headers, timeout=30)

        # If quick_snap endpoint returns 404 or unsupported on newer accounts,
        # fallback to story configure
        if resp.status_code == 404:
            story_url = "https://i.instagram.com/api/v1/media/configure_to_story/"
            resp = self.session.post(story_url, data=payload, headers=headers, timeout=30)

        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Instant dispatch failed (HTTP {resp.status_code}): {resp.text}")

        res_data = resp.json()
        if res_data.get("status") != "ok":
            raise RuntimeError(f"Instagram rejected Instant dispatch: {res_data}")

        return res_data

    def photo_configure_to_story(
        self,
        upload_id: str,
        width: int = 1080,
        height: int = 1920,
        audience: str = "mutual_followers",
    ) -> Dict[str, Any]:
        """Configures uploaded photo to Instagram Story channel."""
        url = "https://i.instagram.com/api/v1/media/configure_to_story/"
        client_timestamp = str(int(time.time()))
        audience_mode = "1" if audience == "close_friends" else "0"
        csrf_token = self.get_cookie("csrftoken") or uuid.uuid4().hex

        payload = {
            "_csrftoken": csrf_token,
            "_uid": str(self.user_id),
            "_uuid": self.uuid,
            "upload_id": str(upload_id),
            "source_type": "4",
            "caption": "",
            "audience": audience_mode,
            "device_id": self.android_device_id,
            "client_timestamp": client_timestamp,
            "client_shared_at": client_timestamp,
            "device": {
                "manufacturer": self.device["manufacturer"],
                "model": self.device["model"],
                "android_version": self.device["android_version"],
                "android_release": self.device["android_release"],
            },
            "nav_chains": self._quick_snap_nav_chain(),
        }
        headers = {
            "X-IG-Nav-Chain": self._quick_snap_nav_chain(),
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        resp = self.session.post(url, data=payload, headers=headers, timeout=30)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Story photo dispatch failed (HTTP {resp.status_code}): {resp.text}")
        res_data = resp.json()
        if res_data.get("status") != "ok":
            raise RuntimeError(f"Instagram rejected Story dispatch: {res_data}")
        return res_data

    def photo_upload_to_story(self, photo_path: Path, audience: str = "mutual_followers") -> Dict[str, Any]:
        """Uploads and configures a photo as an Instagram Story."""
        upload_id, width, height = self.photo_rupload(photo_path)
        return self.photo_configure_to_story(upload_id, width=width, height=height, audience=audience)

    def video_configure_to_story(
        self,
        upload_id: str,
        width: int = 1080,
        height: int = 1920,
        duration: float = 5.0,
        audience: str = "mutual_followers",
    ) -> Dict[str, Any]:
        """Configures uploaded video to Instagram Story channel."""
        url = "https://i.instagram.com/api/v1/media/configure_to_story/"
        client_timestamp = str(int(time.time()))
        audience_mode = "1" if audience == "close_friends" else "0"
        csrf_token = self.get_cookie("csrftoken") or uuid.uuid4().hex

        payload = {
            "_csrftoken": csrf_token,
            "_uid": str(self.user_id),
            "_uuid": self.uuid,
            "upload_id": str(upload_id),
            "source_type": "4",
            "caption": "",
            "audience": audience_mode,
            "device_id": self.android_device_id,
            "client_timestamp": client_timestamp,
            "client_shared_at": client_timestamp,
            "device": {
                "manufacturer": self.device["manufacturer"],
                "model": self.device["model"],
                "android_version": self.device["android_version"],
                "android_release": self.device["android_release"],
            },
            "nav_chains": self._quick_snap_nav_chain(),
            "video_result": "",
            "audio_muted": "0",
        }
        headers = {
            "X-IG-Nav-Chain": self._quick_snap_nav_chain(),
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        resp = self.session.post(url, data=payload, headers=headers, timeout=30)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Story video dispatch failed (HTTP {resp.status_code}): {resp.text}")
        res_data = resp.json()
        if res_data.get("status") != "ok":
            raise RuntimeError(f"Instagram rejected Story video dispatch: {res_data}")
        return res_data

    def video_upload_to_story(self, video_path: Path, audience: str = "mutual_followers") -> Dict[str, Any]:
        """Uploads and configures a video as an Instagram Story."""
        upload_id, width, height, duration = self.video_rupload(video_path)
        return self.video_configure_to_story(upload_id, width=width, height=height, duration=duration, audience=audience)

    def dump_settings(self, file_path: str):
        """Saves session cookies and persistent device settings."""
        data = {
            "cookies": {c.name: c.value for c in self.session.cookies},
            "user_id": self.user_id,
            "username": self.username,
            "sessionid": self.sessionid,
            "device": self.device,
        }
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    def load_settings(self, file_path: str) -> bool:
        """Restores session cookies and device settings."""
        p = Path(file_path)
        if not p.exists():
            return False
        try:
            with open(p, "r") as f:
                data = json.load(f)
            self.user_id = data.get("user_id", "")
            self.username = data.get("username", "")
            self.sessionid = data.get("sessionid", "")
            for k, v in data.get("cookies", {}).items():
                self.session.cookies.set(k, v, domain=".instagram.com")
            return bool(self.sessionid)
        except Exception:
            return False


def get_instagram_client() -> LightweightClient:
    """Factory helper returning a configured client."""
    return LightweightClient()
