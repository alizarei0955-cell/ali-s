import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = os.environ.get("OPENROUTER_MODEL", "mistralai/ministral-3b-2512")

class NexusHandler(BaseHTTPRequestHandler):
    def send_json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            try:
                body = (BASE_DIR / "index.html").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except OSError:
                self.send_error(500, "index.html not found")
        elif self.path == "/health":
            self.send_json(200, {"ok": True, "api_key_configured": bool(API_KEY)})
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_error(404)
            return
        if not API_KEY:
            self.send_json(503, {"error": "کلید OPENROUTER_API_KEY در تنظیمات سرور وارد نشده است."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 100_000:
                self.send_json(400, {"error": "درخواست نامعتبر است."})
                return
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            messages = payload.get("messages", [])
            if not isinstance(messages, list) or not messages:
                self.send_json(400, {"error": "پیامی برای ارسال وجود ندارد."})
                return
            clean_messages = [{"role": "system", "content": "تو NEXUS ENGINEER AI هستی؛ دستیار فارسی‌زبان متخصص الکترونیک، تعمیر برد، برنامه‌نویسی و مهندسی. پاسخ‌ها را دقیق، ایمن و قابل‌فهم بده."}]
            for item in messages[-12:]:
                role = item.get("role")
                content = item.get("content")
                if role in ("user", "assistant") and isinstance(content, str):
                    clean_messages.append({"role": role, "content": content[:8000]})
            request_body = json.dumps({"model": MODEL, "messages": clean_messages, "temperature": 0.5}, ensure_ascii=False).encode("utf-8")
            req = Request(API_URL, data=request_body, headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": os.environ.get("SITE_URL", "https://nexus-engineer-ai.onrender.com"),
                "X-Title": "NEXUS ENGINEER AI",
            }, method="POST")
            with urlopen(req, timeout=45) as response:
                result = json.loads(response.read().decode("utf-8"))
            answer = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not answer:
                self.send_json(502, {"error": "پاسخ خالی از سرویس هوش مصنوعی دریافت شد."})
                return
            self.send_json(200, {"reply": answer})
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1200]
            self.send_json(502, {"error": f"خطای سرویس هوش مصنوعی ({exc.code}). تنظیمات کلید، مدل و اعتبار حساب را بررسی کن.", "detail": detail})
        except (URLError, TimeoutError) as exc:
            self.send_json(502, {"error": "ارتباط با سرویس هوش مصنوعی برقرار نشد. اتصال اینترنت یا وضعیت سرویس را بررسی کن."})
        except (ValueError, KeyError, IndexError, json.JSONDecodeError):
            self.send_json(400, {"error": "داده دریافتی معتبر نیست."})
        except Exception:
            self.send_json(500, {"error": "خطای داخلی سرور رخ داد."})

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    server = HTTPServer(("0.0.0.0", port), NexusHandler)
    print(f"NEXUS ENGINEER AI listening on port {port}")
    server.serve_forever()
