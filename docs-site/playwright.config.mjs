import {defineConfig} from '@playwright/test';
import {content} from './reader/settings.mjs';

export default defineConfig({
  testDir: './tests',
  timeout: 30000,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:' + process.env.READER_PORT + content.product.basePath + '/',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure'
  },
  projects: [
    {name: 'desktop', use: {viewport: {width: 1440, height: 1000}}},
    {name: 'phone', use: {viewport: {width: 390, height: 844}}},
    {name: 'webkit-phone', testMatch: 'platform.spec.mjs', use: {browserName: 'webkit', viewport: {width: 390, height: 844}}}
  ]
});
