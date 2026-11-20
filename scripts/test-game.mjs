import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';

const html = readFileSync(new URL('../puzzle-fantasy-mobile.html', import.meta.url), 'utf8');
const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].map(match => match[1]);
const coreSource = scripts.find(source => source.includes('const PuzzleCore ='));
const core = vm.runInNewContext(coreSource + '\nPuzzleCore;');
const copy = value => JSON.parse(JSON.stringify(value));

test('all shipped JavaScript parses', () => {
  assert.equal(scripts.length, 4);
  for (const source of scripts) new vm.Script(source);
});
test('six categories contain seven real puzzles', () => {
  const puzzles = vm.runInNewContext(scripts[0] + '\npuzzles;');
  assert.equal(puzzles.length, 7);
  assert.equal(new Set(puzzles.map(item => item.id)).size, 7);
  assert.equal(new Set(puzzles.map(item => item.categoryId)).size, 6);
  assert.ok(puzzles.every(item => item.image.startsWith('data:image/')));
});
test('new puzzle contains sixteen unique tray pieces', () => {
  const state = core.create('nature-lake');
  assert.equal(state.pieces.length, 16);
  assert.equal(new Set(state.order).size, 16);
  assert.ok(state.pieces.every(piece => piece.zone === 'tray'));
});
test('all correct drops snap; a distant wrong drop does not', () => {
  const geometry = core.geometry(1.5);
  for (const piece of core.create('nature-lake').pieces) {
    Object.assign(piece, core.target(piece, geometry), {zone:'free'});
    assert.equal(core.settle(piece, geometry), true);
    assert.equal(piece.zone, 'placed');
  }
  const wrong = {id:0, zone:'free', x:400, y:250};
  assert.equal(core.settle(wrong, geometry), false);
  assert.equal(wrong.zone, 'free');
});
test('saved progress survives restoration at a different aspect ratio', () => {
  const state = copy(core.create('nature-lake'));
  state.pieces[3].zone = 'placed';
  state.elapsedMs = 12400;
  const restored = core.restore(state, 'nature-lake', core.geometry(.75));
  assert.equal(restored.pieces[3].zone, 'placed');
  assert.equal(restored.elapsedMs, 12400);
  assert.equal(restored.pieces[3].x, 600);
  assert.equal(restored.complete, false);
});
test('corrupt, duplicate and unrelated saved pieces reset safely', () => {
  const state = copy(core.create('nature-lake'));
  state.pieces[1].id = 0;
  assert.ok(core.restore(state,'nature-lake',core.geometry(1)).pieces.every(piece => piece.zone === 'tray'));
  state.pieces[1].id = 1;
  state.pieces[2].x = null;
  assert.ok(core.restore(state,'nature-lake',core.geometry(1)).pieces.every(piece => piece.zone === 'tray'));
  assert.equal(core.restore(state,'another-puzzle',core.geometry(1)).puzzleId,'another-puzzle');
});
test('completed saved puzzle preserves its final time', () => {
  const state = copy(core.create('nature-lake'));
  for (const piece of state.pieces) piece.zone = 'placed';
  state.elapsedMs = 42000;
  state.finalElapsedMs = 40000;
  const restored = core.restore(state,'nature-lake',core.geometry(1));
  assert.equal(restored.complete,true);
  assert.equal(restored.finalElapsedMs,40000);
});
test('no remote script, stylesheet, tracking or network API is shipped', () => {
  assert.doesNotMatch(html, /<script\b[^>]*\bsrc\s*=/i);
  assert.doesNotMatch(html, /<link\b[^>]*\bhref\s*=/i);
  assert.doesNotMatch(html, /\b(?:fetch|XMLHttpRequest|WebSocket|sendBeacon)\s*\(/);
});
test('approved identity is consistent in web, Capacitor and Android', () => {
  const config = JSON.parse(readFileSync(new URL('../capacitor.config.json',import.meta.url),'utf8'));
  const gradle = readFileSync(new URL('../android/app/build.gradle',import.meta.url),'utf8');
  const strings = readFileSync(new URL('../android/app/src/main/res/values/strings.xml',import.meta.url),'utf8');
  assert.equal(config.appId,'ir.bbehrouz.tikechin');
  assert.equal(config.appName,'تکه‌چین');
  assert.ok(html.includes(`<title>${config.appName}</title>`));
  assert.ok(html.includes(`CONFIG={name:'${config.appName}'`));
  assert.ok(gradle.includes(`applicationId "${config.appId}"`));
  assert.ok(gradle.includes(`namespace = "${config.appId}"`));
  assert.ok(strings.includes(`<string name="app_name">${config.appName}</string>`));
});
