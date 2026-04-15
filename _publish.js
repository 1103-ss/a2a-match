#!/usr/bin/env node
// 直接调用 clawhub publish 并捕获所有输出
const { execSync } = require('child_process');
const path = 'C:/Users/Administrator/.qclaw/workspace/a2a-match';

try {
    const result = execSync(
        `npx clawhub publish "${path}" --version "2.8.0"`,
        { encoding: 'utf8', timeout: 60000, maxBuffer: 10 * 1024 * 1024 }
    );
    console.log('STDOUT:', result);
} catch (e) {
    console.log('EXIT CODE:', e.status);
    console.log('STDOUT:', e.stdout);
    console.log('STDERR:', e.stderr);
}
