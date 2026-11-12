import {test, expect} from '@playwright/test';

test('book links open references and return to the same passage', async ({page}) => {
  await page.goto('./overview/docs-hub/');
  await expect(page.getByRole('heading', {level: 1})).toHaveText('Praxis Docs');
  const link = page.locator('main article a[data-reference]').filter({hasText: /^Event Spine$/}).first();
  await link.scrollIntoViewIfNeeded();
  const before = await link.evaluate(node => node.getBoundingClientRect().top);
  await link.click();
  const reference = page.getByRole('dialog', {name: 'Reference'});
  await expect(reference.getByRole('heading', {level: 1})).toHaveText('Event Spine');
  await reference.getByRole('button', {name: 'Return to chapter'}).click();
  await expect(reference).toBeHidden();
  await expect(link).toBeFocused();
  expect(Math.abs((await link.boundingBox()).y - before)).toBeLessThan(3);
});

test('search opens a wiki article with its authored evidence', async ({page}) => {
  await page.goto('./');
  await page.getByRole('button', {name: 'Search', exact: true}).click();
  await page.getByRole('searchbox').fill('how a record reaches the log');
  await page.getByRole('link', {name: 'How a record reaches the log', exact: true}).click();
  await expect(page.getByRole('heading', {level: 1})).toHaveText('How a record reaches the log');
  await page.getByText('Source evidence', {exact: true}).click();
  await expect(page.locator('article details pre')).toContainText('source: "`nexus/infrastructure/wal.py` 62-64');
  await page.getByRole('link', {name: 'What a damaged record costs', exact: true}).click();
  await expect(page.getByRole('heading', {level: 1})).toHaveText('What a damaged record costs');
});

test('code ranges survive reload and copy the source without line numbers', async ({page, context}) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto('./guides/setup-and-verification/');
  const figure = page.locator('figure.code').first();
  await figure.locator('.line-number').first().focus();
  await page.keyboard.press('Shift+ArrowDown');
  await expect(figure.locator('.selected-line')).toHaveCount(2);
  await page.reload();
  await expect(figure.locator('.selected-line')).toHaveCount(2);
  const source = Buffer.from(await figure.getAttribute('data-source'), 'base64').toString();
  await figure.getByRole('button', {name: 'Copy', exact: true}).click();
  await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe(source);
});
