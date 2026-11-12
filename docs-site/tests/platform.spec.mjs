import {test, expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import {content} from '../reader/settings.mjs';

test('book, reference, developer and wiki pages reflow and meet automated WCAG checks', async ({page}) => {
  for (const route of ['./', './reference/', './developer/home/', './wiki/atoms/how-a-record-reaches-the-log/']) {
    await page.goto(route);
    await page.waitForFunction(() => document.fonts.status === 'loaded');
    await expect(page.getByRole('heading', {level: 1})).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), route).toBe(true);
    const audit = await new AxeBuilder({page}).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
    expect(audit.violations.map(violation => violation.id), route).toEqual([]);
  }
});

test('static routing applies security headers to pages, redirects and errors', async ({request}) => {
  const {basePath} = content.product;
  if (basePath) {
    const redirect = await request.get(basePath, {maxRedirects: 0});
    expect(redirect.status()).toBe(302);
    expect(new URL(redirect.headers().location).pathname).toBe(basePath + '/');
    expect(redirect.headers()['x-frame-options']).toBe('DENY');
  }
  for (const [route, status] of [['./', 200], ['./assets/fonts/archivo.woff2', 200], ['./absent/', 404]]) {
    const response = await request.get(route);
    expect(response.status(), route).toBe(status);
    expect(response.headers()['content-security-policy']).toContain("frame-ancestors 'none'");
  }
});
