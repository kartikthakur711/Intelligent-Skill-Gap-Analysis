import assert from 'node:assert/strict';
import { readFile, readdir } from 'node:fs/promises';

const [requirements, apiRequirements, webPackage, rootPackage, devcontainer, ciWorkflow, readme, workflowNames] = await Promise.all([
  readFile(new URL('../requirements.txt', import.meta.url), 'utf8'),
  readFile(new URL('../requirements-api.txt', import.meta.url), 'utf8'),
  readFile(new URL('../web/package.json', import.meta.url), 'utf8'),
  readFile(new URL('../package.json', import.meta.url), 'utf8'),
  readFile(new URL('../.devcontainer/devcontainer.json', import.meta.url), 'utf8'),
  readFile(new URL('../.github/workflows/ci.yml', import.meta.url), 'utf8'),
  readFile(new URL('../README.md', import.meta.url), 'utf8'),
  readdir(new URL('../.github/workflows/', import.meta.url)),
]);
const workflowContents = await Promise.all(workflowNames.filter((name) => name.endsWith('.yml') || name.endsWith('.yaml'))
  .map((name) => readFile(new URL(`../.github/workflows/${name}`, import.meta.url), 'utf8')));

assert.doesNotMatch(requirements, /(^|\s)streamlit([<=>!~]|\s|$)/im, 'Python runtime requirements must not include Streamlit');
assert.doesNotMatch(apiRequirements, /streamlit/i, 'FastAPI requirements must not include Streamlit');
assert.doesNotMatch(webPackage, /streamlit/i, 'Web application dependencies must not include Streamlit');
assert.doesNotMatch(rootPackage, /streamlit/i, 'Node scripts must not install or launch Streamlit');
assert.doesNotMatch(devcontainer, /streamlit|app\.py|8501/i, 'Dev Container must not retain Streamlit dependencies, launch commands, app paths, or ports');
assert.match(devcontainer, /corepack prepare pnpm@11\.0\.0 --activate/, 'Dev Container must provision the repository-pinned pnpm major version');
assert.match(devcontainer, /requirements\.txt -r requirements-api\.txt/, 'Dev Container must install the FastAPI runtime and model dependencies');
assert.match(devcontainer, /npm run dev:container/, 'Dev Container must launch the web application services');
for (const port of ['3000', '5173', '8000']) {
  assert.match(devcontainer, new RegExp(`\\b${port}\\b`), `Dev Container must expose the configured application port ${port}`);
}
assert.doesNotMatch(workflowContents.join('\n'), /streamlit|python -m streamlit run/i, 'CI and deployment workflows must not install or launch Streamlit');
assert.doesNotMatch(ciWorkflow, /streamlit|app\.py|dashboard_ui\.py|test_app_runtime/i, 'CI must validate the web application, not the removed UI');
assert.doesNotMatch(readme, /streamlit/i, 'Product documentation must describe the supported web application only');
console.log('Web-only architecture checks passed.');
