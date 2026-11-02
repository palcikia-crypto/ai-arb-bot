const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
puppeteer.use(StealthPlugin());

const SITES = [
    { name: 'CardCash', url: 'https://www.cardcash.com/sell-gift-cards/' },
    { name: 'Gameflip', url: 'https://gameflip.com/overview/sell/gift-cards/' },
    { name: 'G2G', url: 'https://www.g2g.com/seller' },
    { name: 'G2A', url: 'https://www.g2a.com/sellers/' },
    { name: 'Kinguin', url: 'https://www.kinguin.net/sell-on-kinguin' },
    { name: 'BuyBackWorld', url: 'https://www.buybackworld.com/sell/gift-cards' },
    { name: 'GCX', url: 'https://gcx.app/sell-gift-cards' },
    { name: 'Prepaid2Cash', url: 'https://www.prepaid2cash.com/' },
    { name: 'CardBix', url: 'https://cardbix.com/rates' },
    { name: 'SellCardNow', url: 'https://sellcardnow.com/rates' },
    { name: 'HighCardRate', url: 'https://highcardrate.com/blog/sell-gift-cards-for-bitcoin-btc-guide' }
];

async function hunt() {
    const browser = await puppeteer.launch({
        executablePath: '/data/data/com.termux/files/usr/bin/chromium',
        headless: 'new',
        args: [
            '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled',
            '--disable-features=IsolateOrigins,site-per-process',
            '--window-size=1366,768'
        ]
    });
    const page = await browser.newPage();
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36');
    await page.setViewport({ width: 1366, height: 768 });

    const results = {};

    for (const site of SITES) {
        console.log(`\n⏳ ${site.name} → ${site.url}`);
        try {
            await page.goto(site.url, { waitUntil: 'domcontentloaded', timeout: 45000 });
            await new Promise(r => setTimeout(r, 7000)); // Ждём рендер JS

            const bodyText = await page.evaluate(() => document.body.innerText);
            const title = await page.title();
            console.log(`   📄 Title: ${title}`);
            console.log(`   📄 Текст: ${bodyText.substring(0, 300).replace(/\s+/g, ' ')}`);

            let found = null;
            let how = '';

            // Способ 1: Regex по тексту "Steam ... XX%"
            let m = bodyText.match(/Steam[^0-9%]{0,80}(\d{2,3})\s*%/i);
            if (m) { found = parseInt(m[1]); how = 'текст'; }

            // Способ 2: Поиск в JSON-скриптах
            if (!found) {
                const jsonMatch = await page.evaluate(() => {
                    for (const s of document.querySelectorAll('script')) {
                        const t = s.textContent || '';
                        if (!/steam/i.test(t)) continue;
                        const m = t.match(/"steam"[^}]{0,500}?"(?:rate|percent|payout|value)"\s*:\s*"?(\d{2,3})/i);
                        if (m) return m[1];
                    }
                    return null;
                });
                if (jsonMatch && parseInt(jsonMatch) >= 50 && parseInt(jsonMatch) <= 95) {
                    found = parseInt(jsonMatch); how = 'inline-JSON';
                }
            }

            // Способ 3: Поиск в DOM-элементах
            if (!found) {
                const domRate = await page.evaluate(() => {
                    for (const el of document.querySelectorAll('[class*="rate"],[class*="percent"],[data-rate],[class*="payout"]')) {
                        const t = (el.textContent || '') + ' ' + (el.getAttribute('data-rate') || '');
                        const m = t.match(/(\d{2,3})\s*%?/);
                        if (m && parseInt(m[1]) >= 50 && parseInt(m[1]) <= 95) return m[1];
                    }
                    return null;
                });
                if (domRate) { found = parseInt(domRate); how = 'DOM-класс'; }
            }

            if (found) {
                results[site.name] = found;
                console.log(`   ✅ ${site.name}: ${found}% (${how})`);
            } else {
                console.log(`   ⚠️ ${site.name}: ставка не найдена`);
            }

        } catch (e) {
            console.error(`   ❌ ${site.name}: ${e.message}`);
        }
    }

    await browser.close();
    console.log('\n=== ИТОГОВЫЙ РЕЗУЛЬТАТ ===');
    console.log(JSON.stringify(results, null, 2));
}

hunt().catch(e => { console.error(e); process.exit(1); });
