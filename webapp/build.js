const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { minify: minifyHtml } = require('html-minifier-terser');
const JavaScriptObfuscator = require('javascript-obfuscator');

const SRC_DIR = path.join(__dirname, 'static');
const DIST_DIR = path.join(__dirname, 'dist');

function ensureDir(p) {
  if (!fs.existsSync(p)) fs.mkdirSync(p, { recursive: true });
}

function hashContent(buf) {
  return crypto.createHash('sha256').update(buf).digest('hex').slice(0, 10);
}

function processHtml(filePath, outDir) {
  const src = fs.readFileSync(filePath, 'utf8');
  return minifyHtml(src, {
    collapseWhitespace: true,
    removeComments: true,
    minifyJS: true,
    minifyCSS: true,
  });
}

function processJsInHtml(html) {
  // Very simple inline <script> obfuscation. For robustness, a bundler is recommended.
  return html.replace(/<script>([\s\S]*?)<\/script>/g, (m, code) => {
    const obf = JavaScriptObfuscator.obfuscate(code, {
      compact: true,
      controlFlowFlattening: true,
      controlFlowFlatteningThreshold: 0.75,
      deadCodeInjection: true,
      deadCodeInjectionThreshold: 0.4,
      stringArray: true,
      stringArrayEncoding: ['base64'],
      stringArrayThreshold: 0.75,
      selfDefending: true,
      transformObjectKeys: true,
      unicodeEscapeSequence: true,
    }).getObfuscatedCode();
    return `<script>${obf}</script>`;
  });
}

async function build() {
  ensureDir(DIST_DIR);
  const indexHtml = path.join(SRC_DIR, 'index.html');
  const htmlMin = await processHtml(indexHtml, DIST_DIR);
  const htmlObf = processJsInHtml(htmlMin);
  const hash = hashContent(Buffer.from(htmlObf, 'utf8'));
  const outName = `index.${hash}.html`;
  fs.writeFileSync(path.join(DIST_DIR, outName), htmlObf);
  // Write an asset map for Flask to find hashed file
  fs.writeFileSync(path.join(DIST_DIR, 'assets.json'), JSON.stringify({ index: outName }, null, 2));
  console.log(`Built ${outName}`);
}

build().catch((e) => { console.error(e); process.exit(1); });


