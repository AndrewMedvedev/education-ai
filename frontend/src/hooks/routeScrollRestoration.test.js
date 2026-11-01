import { test } from 'node:test';
import assert from 'node:assert/strict';
import { restoreRouteScroll } from './routeScrollRestoration.js';

function windowFixture() {
  let callback;
  const listeners = new Map();
  return {
    document: { documentElement: { scrollHeight: 500 } },
    innerHeight: 500, scrollY: 0, writes: 0,
    requestAnimationFrame(fn) { callback = fn; return 1; },
    cancelAnimationFrame() { callback = null; },
    addEventListener(name, fn) { listeners.set(name, fn); },
    removeEventListener(name) { listeners.delete(name); },
    scrollTo({ top }) { this.scrollY = top; this.writes++; },
    frame() { const fn = callback; callback = null; fn?.(); },
    pointer() { listeners.get('pointerdown')?.(); },
  };
}

test('scroll waits beyond 120 frames without moving to a truncated page bottom', () => {
  const win = windowFixture();
  let done = 0;
  restoreRouteScroll(900, win, () => done++);
  for (let index = 0; index < 240; index++) win.frame();
  assert.equal(done, 0);
  assert.equal(win.writes, 0);
  win.document.documentElement.scrollHeight = 1800;
  win.frame();
  assert.equal(win.scrollY, 900);
  assert.equal(done, 1);
});

test('pointer interaction cancels pending restoration before content arrives', () => {
  const win = windowFixture();
  let done = 0;
  restoreRouteScroll(900, win, () => done++);
  win.frame();
  win.pointer();
  win.document.documentElement.scrollHeight = 1800;
  win.frame();
  assert.equal(win.writes, 0);
  assert.equal(done, 1);
});
