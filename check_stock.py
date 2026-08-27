import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://www.terminalx.com/default-category/r898950001?color=1644"
STATE_FILE = Path("state.txt")


def send_email():
    msg = EmailMessage()
    msg["Subject"] = "🟢 Kérastase Discipline חזר למלאי!"
    msg["From"] = os.environ["EMAIL_FROM"]
    msg["To"] = os.environ["EMAIL_TO"]

    msg.set_content(
        "המוצר Kérastase Discipline ללא סולפטים חזר למלאי!\n\n"
        f"לכניסה למוצר:\n{URL}\n"
    )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(
            os.environ["EMAIL_FROM"],
            os.environ["EMAIL_PASSWORD"]
        )
        smtp.send_message(msg)


def check_stock():
    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page(
            locale="he-IL",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            )
        )

        print("Opening:", URL)

        response = page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        print("HTTP:", response.status if response else "NO RESPONSE")

        # נותנים ל-JavaScript של האתר זמן לעבוד
        page.wait_for_timeout(5000)

        title = page.title()
        text = page.locator("body").inner_text().lower()

        print("Page title:", title)
        print("Final URL:", page.url)

        # נשמור צילום מסך במקרה שמשהו לא עובד,
        # כדי שנוכל לראות מה GitHub באמת קיבל.
        page.screenshot(
            path="terminalx.png",
            full_page=True
        )

        # המוצר זמין אם מופיע כפתור רכישה/הוספה לסל.
        purchase_markers = [
            "הוסף לסל",
            "הוספה לסל",
            "הוסיפי לסל",
            "add to cart",
            "add to bag",
        ]

        unavailable_markers = [
            "oops",
            "המוצר אינו זמין",
            "אזל מהמלאי",
            "out of stock",
        ]

        has_purchase_button = any(
            marker in text for marker in purchase_markers
        )

        clearly_unavailable = any(
            marker in text for marker in unavailable_markers
        )

        available = has_purchase_button and not clearly_unavailable

        print("Purchase button:", has_purchase_button)
        print("Clearly unavailable:", clearly_unavailable)
        print("AVAILABLE:", available)

        browser.close()

    return available


available = check_stock()

previous = (
    STATE_FILE.read_text().strip()
    if STATE_FILE.exists()
    else "unknown"
)

print("Previous state:", previous)

# התראה רק במעבר מלא זמין → זמין
if available and previous != "available":
    print("PRODUCT IS AVAILABLE - SENDING EMAIL")
    send_email()
else:
    print("No email needed.")

STATE_FILE.write_text(
    "available" if available else "unavailable"
)
