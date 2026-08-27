import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

import requests

URL = "https://www.terminalx.com/default-category/r898950001?color=1644"
STATE_FILE = Path("state.txt")

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    )
}

r = requests.get(URL, headers=headers, timeout=30)
text = r.text.lower()

# סימנים שהעמוד הוא עמוד מוצר זמין.
available_markers = [
    "הוסף לסל",
    "הוספה לסל",
    "add to cart",
    "add to bag",
]

# במסך הנוכחי Terminal X מציג "Oops" כשהמוצר אינו זמין.
unavailable_markers = [
    "oops",
    "הפריט האחרון במלאי",
]

available = (
    r.status_code == 200
    and any(x in text for x in available_markers)
    and not any(x in text for x in unavailable_markers)
)

previous = STATE_FILE.read_text().strip() if STATE_FILE.exists() else "unknown"

print(f"HTTP: {r.status_code}")
print(f"Available: {available}")
print(f"Previous: {previous}")

# התראה רק כאשר המוצר עובר מלא זמין.
if available and previous != "available":
    msg = EmailMessage()
    msg["Subject"] = "🟢 Kérastase Discipline חזר למלאי!"
    msg["From"] = os.environ["EMAIL_FROM"]
    msg["To"] = os.environ["EMAIL_TO"]
    msg.set_content(
        "המוצר Kérastase Discipline ללא סולפטים חזר למלאי!\n\n"
        f"להזמנה:\n{URL}\n"
    )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(
            os.environ["EMAIL_FROM"],
            os.environ["EMAIL_PASSWORD"]
        )
        smtp.send_message(msg)

# שמירת המצב לבדיקה הבאה
STATE_FILE.write_text("available" if available else "unavailable")
