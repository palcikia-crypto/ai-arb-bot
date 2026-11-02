const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
puppeteer.use(StealthPlugin());

async function getRates() {
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
    await page.setViewport({ width: 1366, height: 768, deviceScaleFactor: 1 });
    await page.setExtraHTTPHeaders({ 'Accept-Language': 'en-US,en;q=0.9' });

    let results = {};

    const sites = [
        { name: 'CardBix', url: 'https://cardbix.com/rates', wait: 'networkidle2', preDelay: 12000 },
        { name: 'SellCardNow', url: 'https://sellcardnow.com/', wait: 'domcontentloaded', preDelay: 10000 },
        { name: 'HighCardRate', url: 'https://highcardrate.com/blog/sell-gift-cards-for-bitcoin-btc-guide', wait: 'domcontentloaded', preDelay: 3000 }
    ];

    for (const site of sites) {
        try {
            console.log(`\n⏳ ${site.name} → ${site.url}`);
            await page.goto(site.url, { waitUntil: site.wait, timeout: 60000 });
            console.log(`   ⏱️  Ждём ${site.preDelay/1000}с (Cloudflare + JS)...`);
            await new Promise(r => setTimeout(r, site.preDelay));

            const bodyText = await page.evaluate(() => document.body.innerText);
            const title = await page.title();
            const preview = bodyText.substring(0, 300).replace(/\s+/g, ' ');
            console.log(`   📄 Title: ${title}`);
            console.log(`   📄 Текст: ${preview}`);

            let found = null, how = '';

            // Способ 1: regex по тексту
            let m = bodyText.match(/Steam[^0-9%]{0,80}(\d{2,3})\s*%/i);
            if (m) { found = parseInt(m[1]); how = 'текст'; }

            // Способ 2: в inline JSON
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

            // Способ 3: по классам DOM
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

            // Способ 4: клик по Steam (для калькуляторов)
            if (!found && (site.name === 'CardBix' || site.name === 'SellCardNow')) {
                console.log(`   🖱️  Пробую найти и кликнуть Steam в калькуляторе...`);
                try {
                    const clicked = await page.evaluate(() => {
                        for (const el of document.querySelectorAll('button, a, div, span, li')) {
                            if (el.children.length === 0 && /^steam$/i.test(el.textContent.trim())) {
                                el.click(); return true;
                            }
                        }
                        // try image-based search
                        for (const img of document.querySelectorAll('img')) {
                            if (/steam/i.test(img.alt || '') || /steam/i.test(img.src || '')) {
                                img.click(); return true;
                            }
                        }
                        return false;
                    });
                    if (clicked) {
                        console.log(`   ✅ Клик сработал, ждём 5с...`);
                        await new Promise(r => setTimeout(r, 5000));
                        const newText = await page.evaluate(() => document.body.innerText);
                        const m2 = newText.match(/Steam[^0-9%]{0,80}(\d{2,3})\s*%/i);
                        if (m2) { found = parseInt(m2[1]); how = 'клик-Steam'; }
                        else {
                            // ищем в JSON после клика
                            const afterClick = await page.evaluate(() => {
                                for (const s of document.querySelectorAll('script')) {
                                    const t = s.textContent || '';
                                    const m = t.match(/"(?:rate|percent|payout)"\s*:\s*"?(\d{2,3})/i);
                                    if (m) return m[1];
                                }
                                return null;
                            });
                            if (afterClick && parseInt(afterClick) >= 50) {
                                found = parseInt(afterClick); how = 'клик+JSON';
                            }
                        }
                    }
                } catch (e) { console.log(`   ⚠️ Клик: ${e.message}`); }
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
    console.log('\n=== РЕЗУЛЬТАТ ===');
    console.log(JSON.stringify(results, null, 2));
}

getRates().catch(e => { console.error(e); process.exit(1); });
