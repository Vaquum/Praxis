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

test('static routing applies security headers to pages, redirects and errors', async ({request, baseURL}) => {
  const {basePath} = content.product;
  if (basePath) {
    const redirect = await request.get(basePath, {maxRedirects: 0});
    expect(redirect.status()).toBe(302);
    expect(redirect.headers().location).toBe(new URL(basePath + '/', baseURL).href);
    expect(redirect.headers()['x-frame-options']).toBe('DENY');
  }
  for (const [route, status] of [['./', 200], ['./assets/fonts/archivo.woff2', 200], ['./absent/', 404]]) {
    const response = await request.get(route);
    expect(response.status(), route).toBe(status);
    expect(response.headers()['content-security-policy']).toContain("frame-ancestors 'none'");
  }
});

test('search fades in and out and restores focus, with an immediate reduced-motion path', async ({page}) => {
  await page.emulateMedia({reducedMotion: 'no-preference'});
  await page.goto('./');
  const opener = page.getByRole('button', {name: 'Search', exact: true});
  await expect(opener).toBeVisible();
  const dialog = page.locator('[data-search-dialog]');
  await opener.evaluate(button => {
    const panel = document.querySelector('[data-search-dialog]');
    window.searchMotion = {};
    panel.addEventListener('transitionrun', event => {
      if (event.target === panel && event.propertyName === 'opacity') {
        window.searchMotion[panel.hasAttribute('data-closing') ? 'exit' : 'enter'] = true;
      }
    });
    button.focus();
    button.click();
  });
  await expect.poll(() => page.evaluate(() => window.searchMotion.enter)).toBe(true);
  await expect(dialog.getByRole('searchbox')).toBeFocused();
  await page.keyboard.press('Escape');
  await expect.poll(() => page.evaluate(() => window.searchMotion.exit)).toBe(true);
  await expect(dialog).toBeHidden();
  await expect(opener).toBeFocused();

  await page.emulateMedia({reducedMotion: 'reduce'});
  await opener.evaluate(button => button.click());
  expect(await dialog.evaluate(panel => panel.getAnimations().length)).toBe(0);
  await dialog.getByRole('button', {name: 'Close', exact: true}).evaluate(button => button.click());
  await expect(dialog).toBeHidden();
  await expect(opener).toBeFocused();
});

test('chapter navigation crossfades only when motion is enabled', async ({page}) => {
  await page.emulateMedia({reducedMotion: 'no-preference'});
  await page.addInitScript(() => {
    addEventListener('pagereveal', event => {
      window.chapterTransition = Boolean(event.viewTransition);
    });
  });
  await page.goto('./');
  test.skip(!await page.evaluate(() => 'onpagereveal' in window), 'Requires native document transitions');
  const parts = page.getByRole('navigation', {name: 'Parts'});
  await parts.getByRole('link', {name: 'Developer', exact: true}).click();
  await expect(page).toHaveURL(/developer\/home\/$/);
  await expect.poll(() => page.evaluate(() => window.chapterTransition)).toBe(true);

  await page.emulateMedia({reducedMotion: 'reduce'});
  await parts.getByRole('link', {name: 'Book', exact: true}).click();
  await expect(page).toHaveURL(/\/praxis\/$/);
  await expect.poll(() => page.evaluate(() => window.chapterTransition)).toBe(false);
});
