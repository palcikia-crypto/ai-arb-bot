const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const { execSync } = require('child_process');
puppeteer.use(StealthPlugin());

const SITES = [
    { name: 'SellCardNow', url: 'https://sellcardnow.com/' },
    { name: 'HighCardRate', url: 'https://highcardrate.com/blog/sell-gift-cards-for-bitcoin-btc-guide' }
];

async function getDOM(page) {
    return await page.evaluate(() => {
        const text = document.body.innerText.substring(0, 3500);
        const els = [];
        const seen = new Set();
        // Собираем ВСЁ кликабельное, включая div/spans с data-атрибутами (кастомные dropdown)
        for (const el of document.querySelectorAll('button, a, input, select, [role="button"], [role="combobox"], [data-value], [data-card], [onclick], [tabindex]')) {
            if (els.length >= 60) break;
            const r = el.getBoundingClientRect();
            if (r.width === 0 && r.height === 0) continue;
            const t = (el.innerText || el.value || el.placeholder || el.getAttribute('aria-label') || el.getAttribute('data-value') || '').trim().substring(0, 50);
            if (!t && el.tagName !== 'INPUT') continue;
            const key = el.tagName + '|' + t + '|' + (el.id || '');
            if (seen.has(key)) continue;
            seen.add(key);
            els.push({ tag: el.tagName.toLowerCase(), text: t, id: el.id || null, dataValue: el.getAttribute('data-value') || null, role: el.getAttribute('role') || null });
        }
        return { text, els };
    });
}

function askAI(prompt) {
    try {
        const r = execSync('python3 ai_helper.py', {
            input: prompt, timeout: 120000, maxBuffer: 10 * 1024 * 1024,
            encoding: 'utf-8', cwd: '/data/data/com.termux/files/home/ai_arb'
        });
        return r.trim();
    } catch (e) { return null; }
}

async function clickByText(page, text) {
    if (!text) return false;
    return await page.evaluate((t) => {
        const tl = t.toLowerCase().trim();
        // Сначала точное совпадение, потом включение
        const nodes = Array.from(document.querySelectorAll('button, a, div, span, li, [role="button"], [role="combobox"], [data-value], [data-card]'));
        for (const el of nodes) {
            const txt = (el.textContent || '').trim().toLowerCase();
            const dv = (el.getAttribute('data-value') || '').toLowerCase();
            if (txt === tl || dv === tl) { el.click(); return 'exact'; }
        }
        for (const el of nodes) {
            if (el.children.length > 3) continue;
            const txt = (el.textContent || '').trim().toLowerCase();
            if (txt.includes(tl) || tl.includes(txt.slice(0, 10)) && txt.length > 2) { el.click(); return 'partial'; }
        }
        return false;
    }, text);
}

async function main() {
    const browser = await puppeteer.launch({
        executablePath: '/data/data/com.termux/files/usr/bin/chromium',
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled']
    });
    const page = await browser.newPage();
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36');
    await page.setViewport({ width: 1366, height: 900 });
    const results = {};

    for (const site of SITES) {
        console.log('\n>>> ' + site.name);
        try {
            await page.goto(site.url, { waitUntil: 'networkidle2', timeout: 45000 });
            await new Promise(r => setTimeout(r, 8000));
            const history = new Set();
            let found = null;

            for (let step = 1; step <= 7; step++) {
                const dom = await getDOM(page);
                if (dom.text.includes('Performing security verification') || dom.text.includes('Just a moment')) {
                    console.log('  ❌ CF'); break;
                }
                console.log('  step' + step + ': els=' + dom.els.length);

                const prompt = `Ты агент парсинга. Найти ставку продажи Steam gift card 10 USD (процент, который заплатят).

ПРАВИЛА:
1. Ставка 50-95%. <30% — не ставка.
2. Если магазин (продаёт карты) → skip.
3. Скупщик с калькулятором: выбери "Steam", потом "10" / "10 USD", потом нажми Calculate/Check/Get price.
4. Если нажимаешь — в поле "text" напиши ТОЧНЫЙ видимый текст элемента для клика.
5. Не повторяй действия из списка: ${Array.from(history).join('; ')}

JSON:
{"rate": число|null, "action": "click"|"skip"|"none", "text": "точный текст для клика", "reason": "почему"}

DOM:
${JSON.stringify(dom)}`;

                const resp = askAI(prompt);
                if (!resp) { console.log('  AI пусто'); break; }
                let d;
                try { const m = resp.match(/\{[\s\S]*\}/); d = JSON.parse(m ? m[0] : resp); }
                catch (e) { console.log('  parse err'); break; }

                console.log(`  🧠 rate=${d.rate} action=${d.action}${d.text ? ' text="' + d.text + '"' : ''} | ${(d.reason||'').substring(0,60)}`);

                if (d.action === 'skip') { console.log('  skip'); break; }
                if (d.rate && d.rate >= 50 && d.rate <= 95) { results[site.name] = d.rate; console.log(`  ✅ ${d.rate}%`); found = d.rate; break; }
                if (d.action === 'none') break;

                if (d.action === 'click' && d.text) {
                    const key = 'click|' + d.text;
                    if (history.has(key)) { console.log('  🔁 повтор'); break; }
                    history.add(key);
                    const ok = await clickByText(page, d.text);
                    console.log('  click "' + d.text + '": ' + (ok ? 'OK' : 'FAIL'));
                    if (!ok) break;
                    await new Promise(r => setTimeout(r, 4000));
                } else break;
            }
            if (!found) console.log(`  ⚠️ не найдено`);
        } catch (e) { console.error('  ERR:', e.message.substring(0, 100)); }
    }

    await browser.close();
    console.log('\n=== FINAL ===');
    console.log(JSON.stringify(results, null, 2));
}

main().catch(e => { console.error(e); process.exit(1); });
