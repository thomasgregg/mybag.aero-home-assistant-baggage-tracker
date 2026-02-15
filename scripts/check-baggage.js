const { chromium } = require('playwright');

const URL = process.env.BAG_URL || 'https://mybag.aero/baggage/#/pax/austrian/en-gb/delayed/manage-bag';
const REFERENCE = process.env.BAG_REFERENCE || 'BEROS22525';
const FAMILY_NAME = process.env.BAG_FAMILY_NAME || 'Gregg';
const SEARCHING_TEXT = 'SEARCHING FOR YOUR BAGGAGE';
const HEADLESS = (process.env.PLAYWRIGHT_HEADLESS || 'true').toLowerCase() !== 'false';
const USER_AGENT =
  process.env.BAG_USER_AGENT ||
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36';

async function dismissCookieOverlay(page) {
  const actions = [
    '#onetrust-accept-btn-handler',
    '#accept-recommended-btn-handler',
    '#close-pc-btn-handler',
    '.onetrust-close-btn-handler',
  ];

  for (const selector of actions) {
    const button = page.locator(selector).first();
    if ((await button.count()) > 0) {
      await button.click({ timeout: 2000 }).catch(() => {});
    }
  }

  await page.evaluate(() => {
    const overlay = document.querySelector('.onetrust-pc-dark-filter');
    if (overlay) overlay.remove();
    const center = document.querySelector('#onetrust-pc-sdk');
    if (center) center.remove();
  });
}

async function fillLogin(page) {
  await page.locator('#mngRptRefNoLTxt, #mngRptLastNameTxt').first().waitFor({ timeout: 30000 });

  await dismissCookieOverlay(page);

  const idReference = page.locator('#mngRptRefNoLTxt');
  const idFamilyName = page.locator('#mngRptLastNameTxt');
  if ((await idReference.count()) > 0 && (await idFamilyName.count()) > 0) {
    await idReference.fill(REFERENCE);
    await idFamilyName.fill(FAMILY_NAME);

    const idSubmit = page.locator('#mngRptLoginBtn');
    if ((await idSubmit.count()) > 0) {
      await dismissCookieOverlay(page);
      await idSubmit.click();
      return;
    }
  }

  const refCandidates = [
    page.getByLabel(/reference/i),
    page.getByPlaceholder(/reference/i),
    page.getByRole('textbox', { name: /reference/i }),
    page.locator('input[name*="reference" i], input[id*="reference" i], input[id*="refno" i]'),
  ];

  const nameCandidates = [
    page.getByLabel(/family|last name|surname/i),
    page.getByPlaceholder(/family|last name|surname/i),
    page.getByRole('textbox', { name: /family|last name|surname/i }),
    page.locator('input[name*="family" i], input[name*="surname" i], input[id*="family" i], input[id*="surname" i], input[id*="lastname" i]'),
  ];

  let refField = null;
  for (const candidate of refCandidates) {
    if ((await candidate.count()) > 0) {
      refField = candidate.first();
      break;
    }
  }

  let nameField = null;
  for (const candidate of nameCandidates) {
    if ((await candidate.count()) > 0) {
      nameField = candidate.first();
      break;
    }
  }

  if (!refField || !nameField) {
    const textboxes = page.locator('input[type="text"], input:not([type])');
    const count = await textboxes.count();
    if (count >= 2) {
      refField = textboxes.nth(0);
      nameField = textboxes.nth(1);
    } else {
      throw new Error('Unable to find login input fields for reference and family name.');
    }
  }

  await refField.fill(REFERENCE);
  await nameField.fill(FAMILY_NAME);

  const submitCandidates = [
    page.getByRole('button', { name: /manage|find|continue|search|submit|next/i }),
    page.locator('button[type="submit"]'),
    page.locator('input[type="submit"]'),
  ];

  for (const candidate of submitCandidates) {
    if ((await candidate.count()) > 0) {
      await dismissCookieOverlay(page);
      await candidate.first().click();
      return;
    }
  }

  await nameField.press('Enter');
}

async function openBaggageDetails(page) {
  const baggageDetails = page.getByText(/baggage details/i).first();
  await baggageDetails.waitFor({ timeout: 15000 });
  await baggageDetails.click();
}

async function run() {
  const browser = await chromium.launch({ headless: HEADLESS });
  const context = await browser.newContext({ userAgent: USER_AGENT });
  const page = await context.newPage();

  try {
    await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await fillLogin(page);

    await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
    const postLoginText = (await page.locator('body').innerText()).toUpperCase();
    if (postLoginText.includes('NO RECORD WAS FOUND')) {
      throw new Error('No record found for the provided reference number and family name.');
    }

    await openBaggageDetails(page);
    await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});

    const bodyText = (await page.locator('body').innerText()).toUpperCase();
    const isSearching = bodyText.includes(SEARCHING_TEXT);

    const result = {
      checkedAt: new Date().toISOString(),
      reference: REFERENCE,
      familyName: FAMILY_NAME,
      status: isSearching ? 'NEGATIVE' : 'POSITIVE',
      message: isSearching
        ? 'Still searching for your baggage.'
        : 'Good news: status changed from SEARCHING FOR YOUR BAGGAGE.',
      matchedText: isSearching ? SEARCHING_TEXT : null,
    };

    console.log(JSON.stringify(result));
  } finally {
    await browser.close();
  }
}

run().catch((error) => {
  const failure = {
    checkedAt: new Date().toISOString(),
    status: 'ERROR',
    message: error.message,
  };
  console.error(JSON.stringify(failure));
  process.exit(1);
});
