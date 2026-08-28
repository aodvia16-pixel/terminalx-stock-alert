import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
from playwright.sync_api import sync_playwright

SEARCH_TERM = "קרסטס דיספלין ללא סולפטים"
SEARCH_URL = "https://www.terminalx.com/search?q=" + SEARCH_TERM
STATE_FILE = Path("state.txt")


def send_email(product_url, product_name):
    msg = EmailMessage()
    msg["Subject"] = "🟢 Kérastase Discipline חזר למלאי!"
    msg["From"] = os.environ["EMAIL_FROM"]
    msg["To"] = os.environ["EMAIL_TO"]

    msg.set_content(
        f"המוצר נמצא שוב ב-Terminal X:\n\n"
        f"{product_name}\n\n"
        f"כניסה למוצר:\n{product_url}\n"
    )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(
            os.environ["EMAIL_FROM"],
            os.environ["EMAIL_PASSWORD"]
        )
        smtp.send_message(msg)


def check_stock():
    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)

        page = browser.new_page(
            locale="he-IL",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            )
        )

        print("Searching for:", SEARCH_TERM)

        response = page.goto(
            SEARCH_URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        print(
            "HTTP:",
            response.status if response else "NO RESPONSE"
        )

        page.wait_for_timeout(5000)

        print("Search final URL:", page.url)

        # צילום מסך של תוצאות החיפוש
        page.screenshot(
            path="terminalx-search.png",
            full_page=True
        )

        body_text = page.locator("body").inner_text()

        print("Search page text:")
        print(body_text[:5000])

        # מחפשים קישורים שנראים כמו עמודי מוצר.
        links = page.locator("a").all()

        candidates = []

        for link in links:
            try:
                text = link.inner_text().strip()
                href = link.get_attribute("href")

                if not href:
                    continue

                combined = text.lower()

                # התאמה לשם המוצר.
                if (
                    "displine" in combined
                    or "discipline" in combined
                    or "דיספלין" in combined
                    or "ללא סולפטים" in combined
                ):
                    if href.startswith("/"):
                        href = "https://www.terminalx.com" + href

                    candidates.append(
                        (text, href)
                    )

            except Exception:
                pass

        print("Candidates found:", len(candidates))

        for text, href in candidates[:10]:
            print("CANDIDATE:", text, href)

        # אם אין תוצאה בכלל - המוצר לא נמצא בחיפוש.
        if not candidates:
            browser.close()
            return False, None, None

        # ננסה את התוצאה הראשונה שנראית רלוונטית.
        for product_name, product_url in candidates[:5]:

            print("Opening candidate:", product_url)

            try:
                product_page = browser.new_page(
                    locale="he-IL",
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/131.0.0.0 Safari/537.36"
                    )
                )

                product_page.goto(
                    product_url,
                    wait_until="domcontentloaded",
                    timeout=60000
                )

                product_page.wait_for_timeout(4000)

                product_text = (
                    product_page
                    .locator("body")
                    .inner_text()
                    .lower()
                )

                product_page.screenshot(
                    path="terminalx-product.png",
                    full_page=True
                )

                print(
                    "Product HTTP/current URL:",
                    product_page.url
                )

                # סימנים שהמוצר לא באמת קיים/זמין.
                unavailable = [
                    "oops",
                    "המוצר אינו זמין",
                    "לא ניתן למצוא את המוצר",
                    "המוצר לא נמצא",
                    "אזל מהמלאי",
                    "out of stock",
                    "product not found",
                ]

                # סימנים שמדובר בעמוד מוצר תקין.
                product_markers = [
                    "kerastase",
                    "קרסטס",
                    "discipline",
                    "דיספלין",
                    "ללא סולפטים",
                ]

                is_product = any(
                    marker in product_text
                    for marker in product_markers
                )

                is_unavailable = any(
                    marker in product_text
                    for marker in unavailable
                )

                available = is_product and not is_unavailable

                print("Looks like product:", is_product)
                print("Looks unavailable:", is_unavailable)
                print("AVAILABLE:", available)

                product_page.close()

                if available:
                    browser.close()
                    return True, product_url, product_name

            except Exception as e:
                print("Candidate failed:", e)

        browser.close()

        return False, None, None


available, product_url, product_name = check_stock()

previous = (
    STATE_FILE.read_text().strip()
    if STATE_FILE.exists()
    else "unknown"
)

print("Previous state:", previous)
print("Current state:", "available" if available else "unavailable")

if available and previous != "available":

    print("PRODUCT FOUND - SENDING EMAIL")

    send_email(
        product_url,
        product_name
    )

else:

    print("No email needed.")

STATE_FILE.write_text(
    "available" if available else "unavailable"
)
