import json
import asyncio
import os
from playwright.async_api import async_playwright

USERNAME = os.environ.get("NUVOLA_USERNAME")
PASSWORD = os.environ.get("NUVOLA_PASSWORD")

async def fetch_nuvola_homework():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("Navigating to Nuvola login...")
        await page.goto("https://nuvola.madisoft.it/login")

        try:
            await page.fill("input#username, input[name='username'], input[name='_username'], input[type='text']", USERNAME)
            await page.fill("input#password, input[name='password'], input[name='_password'], input[type='password']", PASSWORD)
            await page.click("button[type='submit'], input[type='submit']")
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception as e:
            print(f"Login notice: {e}")

        print("Clicking 'Compiti' in the menu...")
        try:
            await page.click("a:has-text('Compiti')")
            await page.wait_for_load_state("networkidle")
        except:
            pass

        print("Switching to weekly view ('settimana')...")
        try:
            await page.click("text=settimana")
            await page.wait_for_timeout(3000)
        except:
            pass

        all_parsed_homework = []

        # Scan Current Week + Next Week
        for week_num in range(2):
            print(f"Extracting assignments for week {week_num + 1}...")
            
            homework_list = await page.evaluate("""() => {
                const results = [];
                const knownSubjects = ["ITALIANO", "GEOGRAFIA", "MATEMATICA", "STORIA", "INGLESE", "SCIENZE", "FISICA", "ARTE", "TECNOLOGIA", "ED. CIVICA", "MUSICA"];
                
                // Target all card elements containing text blocks inside the weekly view
                const cards = document.querySelectorAll('div');
                
                cards.forEach(card => {
                    const text = card.innerText ? card.innerText.trim() : '';
                    
                    // Look for blocks that look like homework entries based on Nuvola's structure
                    if (text.includes('Compiti assegnati') && text.length > 15 && text.length < 800) {
                        let foundSubject = "Generale";
                        const upperText = text.toUpperCase();
                        for (let sub of knownSubjects) {
                            if (upperText.includes(sub)) {
                                foundSubject = sub.charAt(0) + sub.slice(1).toLowerCase();
                                break;
                            }
                        }
                        
                        // Avoid duplicates nested inside parent divs
                        if (!results.some(r => r.content === text) && !results.some(r => text.includes(r.content) && text.length > r.content.length + 50)) {
                            results.push({
                                subject: foundSubject,
                                content: text
                            });
                        }
                    }
                });
                
                return results;
            }""")

            for item in homework_list:
                note_text = item['content']
                task_id = f"nuv-w{week_num}-{abs(hash(note_text)) % 100000}"
                
                if not any(t['note'] == note_text for t in all_parsed_homework):
                    all_parsed_homework.append({
                        "id": task_id,
                        "subject": item['subject'],
                        "note": note_text,
                        "status": "not-started"
                    })

            if week_num == 0:
                print("Moving to next week...")
                try:
                    await page.click("button:has(i.fa-chevron-right), button:has(.fa-angle-right)")
                    await page.wait_for_timeout(3000)
                except:
                    break

        with open("homework_data.json", "w", encoding="utf-8") as f:
            json.dump(all_parsed_homework, f, ensure_ascii=False, indent=2)

        print(f"Successfully saved {len(all_parsed_homework)} assignments to homework_data.json!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(fetch_nuvola_homework())
