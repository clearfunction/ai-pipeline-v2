"""
Vue SPA template generator using Vite + TypeScript.
Replicates the exact output of create-vue with TypeScript and testing.
"""

from typing import List, Any
from templates.base_template_generator import BaseTemplateGenerator, GeneratedCode


class VueSPATemplateGenerator(BaseTemplateGenerator):
    """Generates Vue SPA projects with Vite and TypeScript."""
    
    def __init__(self):
        super().__init__('vue_spa')
    
    def generate_project_scaffold(self, project_name: str, architecture: Any) -> List[GeneratedCode]:
        """Generate complete Vue SPA project scaffold."""
        self.logger.info(f"Generating Vue SPA project: {project_name}")
        
        project_name = self._sanitize_project_name(project_name)
        generated_files = []
        
        # Generate all scaffold files
        templates = {
            'package.json': self._get_package_json(project_name),
            'vite.config.ts': self._get_vite_config(),
            'tsconfig.json': self._get_tsconfig(),
            'tsconfig.app.json': self._get_tsconfig_app(),
            'tsconfig.node.json': self._get_tsconfig_node(),
            'tsconfig.vitest.json': self._get_tsconfig_vitest(),
            'env.d.ts': self._get_env_dts(),
            'playwright.config.ts': self._get_playwright_config(),
            'index.html': self._get_index_html(project_name),
            '.gitignore': self._get_gitignore(),
            'README.md': self._get_readme(project_name),
            'src/App.vue': self._get_app_vue(),
            'src/main.ts': self._get_main_ts(),
            'src/assets/main.css': self._get_style_css(),
            'src/components/Counter.vue': self._get_counter_component(),
            'src/components/HelloWorld.vue': self._get_hello_world_component(),
            'src/composables/useCounter.ts': self._get_use_counter_composable(),
            'src/types/index.ts': self._get_types(),
            'src/utils/constants.ts': self._get_constants(),
            'src/tests/App.test.ts': self._get_app_test(),
            'src/tests/components/Counter.test.ts': self._get_counter_test(),
            'src/tests/composables/useCounter.test.ts': self._get_use_counter_test(),
            'src/tests/setup.ts': self._get_test_setup(),
            'vitest.config.ts': self._get_vitest_config(),
            'vitest.config.component.ts': self._get_vitest_component_config(),
            'playwright.config.ts': self._get_playwright_config(),
            'playwright-visual.config.ts': self._get_playwright_visual_config(),
            'playwright-smoke.config.ts': self._get_playwright_smoke_config(),
            'tests/e2e/app.spec.ts': self._get_e2e_test()
        }
        
        for file_path, content in templates.items():
            generated_files.append(
                self._create_generated_code(file_path, content)
            )
        
        self.logger.info(f"Generated {len(generated_files)} Vue SPA files")
        return generated_files
    
    def get_supported_runtime(self) -> str:
        return 'node'
    
    def get_description(self) -> str:
        return 'Vue 3 + Vite + TypeScript SPA with comprehensive testing (Vitest + Playwright)'
    
    def _get_package_json(self, project_name: str) -> str:
        """Generate package.json with comprehensive test scripts."""
        return f'''{{
  "name": "{project_name}",
  "version": "0.0.1",
  "private": true,
  "scripts": {{
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "preview": "vite preview",
    "test": "vitest run --exclude tests/e2e/**",
    "test:unit": "vitest run --exclude tests/e2e/**",
    "test:component": "vitest run --config vitest.config.component.ts",
    "test:coverage": "vitest run --coverage",
    "test:watch": "vitest --watch",
    "test:e2e": "playwright test",
    "test:a11y": "axe src/components --ext .vue",
    "test:visual": "playwright test --config playwright-visual.config.ts",
    "test:smoke": "playwright test --config playwright-smoke.config.ts",
    "build:analyze": "vite-bundle-analyzer dist/stats.json",
    "lint": "eslint . --ext .vue,.js,.jsx,.cjs,.mjs,.ts,.tsx,.cts,.mts --fix --ignore-path .gitignore",
    "type-check": "vue-tsc --noEmit"
  }},
  "dependencies": {{
    "vue": "^3.4.21"
  }},
  "devDependencies": {{
    "@playwright/test": "^1.42.1",
    "@rushstack/eslint-patch": "^1.3.3",
    "@tsconfig/node18": "^18.2.2",
    "@types/jsdom": "^21.1.6",
    "@types/node": "^18.19.21",
    "@vitejs/plugin-vue": "^5.0.4",
    "@vue/eslint-config-prettier": "^8.0.0",
    "@vue/eslint-config-typescript": "^12.0.0",
    "@vue/test-utils": "2.4.4",
    "@vue/tsconfig": "^0.5.1",
    "axe-core": "^4.8.4",
    "eslint": "^8.57.0",
    "eslint-plugin-playwright": "^1.5.2",
    "eslint-plugin-vue": "^9.20.1",
    "jsdom": "^24.0.0",
    "npm-run-all2": "^6.1.2",
    "playwright": "^1.42.1",
    "prettier": "^3.2.5",
    "typescript": "~5.4.0",
    "vite": "^5.1.6",
    "vite-bundle-analyzer": "^0.7.0",
    "vitest": "1.4.0",
    "@vitest/coverage-v8": "^1.4.0",
    "vue-tsc": "^2.0.6"
  }}
}}'''
    
    # Removed stub package-lock.json generation - will be created by npm install
    # def _get_package_lock_json(self, project_name: str) -> str:
    #     """Generate basic package-lock.json structure."""
    #     # This was causing npm ci failures because it didn't contain actual dependency resolution
    
    def _get_vite_config(self) -> str:
        """Generate Vite configuration."""
        return '''import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 4173,
    host: true
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  }
})'''
    
    def _get_tsconfig(self) -> str:
        """Generate TypeScript configuration."""
        return '''{
  "files": [],
  "references": [
    {
      "path": "./tsconfig.node.json"
    },
    {
      "path": "./tsconfig.app.json"
    },
    {
      "path": "./tsconfig.vitest.json"
    }
  ]
}'''
    
    def _get_tsconfig_app(self) -> str:
        """Generate TypeScript app configuration."""
        return '''{
  "extends": "@vue/tsconfig/tsconfig.dom.json",
  "include": [
    "env.d.ts",
    "src/**/*",
    "src/**/*.vue"
  ],
  "exclude": [
    "src/**/__tests__/*",
    "src/**/*.spec.ts",
    "src/**/*.test.ts"
  ],
  "compilerOptions": {
    "composite": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}'''
    
    def _get_tsconfig_vitest(self) -> str:
        """Generate TypeScript Vitest configuration."""
        return '''{
  "extends": "./tsconfig.app.json",
  "exclude": [],
  "include": [
    "src/**/__tests__/*",
    "src/**/*.spec.ts",
    "src/**/*.test.ts"
  ],
  "compilerOptions": {
    "composite": true,
    "lib": [],
    "types": ["node", "jsdom"]
  }
}'''
    
    def _get_env_dts(self) -> str:
        """Generate TypeScript environment declarations."""
        return '''/// <reference types="vite/client" />
'''
    
    def _get_playwright_config(self) -> str:
        """Generate Playwright configuration."""
        return '''import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
})
'''
    
    def _get_tsconfig_node(self) -> str:
        """Generate Node TypeScript configuration."""
        return '''{
  "extends": "@tsconfig/node18/tsconfig.json",
  "include": [
    "vite.config.*",
    "vitest.config.*",
    "cypress.config.*",
    "playwright.config.*"
  ],
  "compilerOptions": {
    "composite": true,
    "module": "ESNext",
    "types": ["node"]
  }
}'''
    
    def _get_index_html(self, project_name: str) -> str:
        """Generate index.html."""
        return f'''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <link rel="icon" href="/favicon.ico">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name}</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>'''
    
    def _get_gitignore(self) -> str:
        """Generate .gitignore."""
        return '''# Logs
logs
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*
pnpm-debug.log*
lerna-debug.log*

node_modules
.DS_Store
dist
dist-ssr
coverage
*.local

/cypress/videos/
/cypress/screenshots/

# Editor directories and files
.vscode/*
!.vscode/extensions.json
.idea
*.suo
*.ntvs*
*.njsproj
*.sln
*.sw?

# Playwright
test-results/
playwright-report/
playwright/.cache/

# Environment variables
.env
.env.local
.env.development.local
.env.test.local
.env.production.local'''
    
    def _get_readme(self, project_name: str) -> str:
        """Generate README.md."""
        return f'''# {project_name}

Vue 3 SPA built with Vite and TypeScript.

## Getting Started

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Run tests
npm run test

# Run E2E tests
npm run test:e2e
```

## Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run test` - Run tests in watch mode
- `npm run test:unit` - Run unit tests once
- `npm run test:component` - Run component tests
- `npm run test:coverage` - Run tests with coverage
- `npm run test:e2e` - Run E2E tests
- `npm run test:visual` - Run visual regression tests
- `npm run type-check` - Type checking
- `npm run lint` - Lint code
'''
    
    def _get_app_vue(self) -> str:
        """Generate main App component."""
        return '''<template>
  <header>
    <div class="wrapper">
      <HelloWorld msg="Vue 3 SPA" />
      <nav>
        <Counter />
      </nav>
    </div>
  </header>

  <main>
    <div class="card">
      <p>Built with Vite and TypeScript</p>
    </div>
  </main>
</template>

<script setup lang="ts">
import HelloWorld from './components/HelloWorld.vue'
import Counter from './components/Counter.vue'
</script>

<style scoped>
header {
  line-height: 1.5;
  max-height: 100vh;
}

.wrapper {
  display: flex;
  place-items: flex-start;
  flex-wrap: wrap;
}

nav {
  width: 100%;
  font-size: 12px;
  text-align: center;
  margin-top: 2rem;
}

main {
  padding: 2rem;
}

.card {
  padding: 2em;
  background-color: #f9f9f9;
  border-radius: 8px;
  margin: 1rem 0;
}
</style>'''
    
    def _get_main_ts(self) -> str:
        """Generate main.ts entry point."""
        return '''import './assets/main.css'
import { createApp } from 'vue'
import App from './App.vue'

createApp(App).mount('#app')'''
    
    def _get_style_css(self) -> str:
        """Generate main style.css."""
        return '''*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  font-weight: normal;
}

body {
  min-height: 100vh;
  color: #2c3e50;
  background: #ffffff;
  transition: color 0.5s, background-color 0.5s;
  line-height: 1.6;
  font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu,
    Cantarell, 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
  font-size: 15px;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app {
  max-width: 1280px;
  margin: 0 auto;
  padding: 2rem;
  font-weight: normal;
}'''
    
    def _get_counter_component(self) -> str:
        """Generate Counter component."""
        return '''<template>
  <div class="counter">
    <h2>Counter Component</h2>
    <p>Count: {{ count }}</p>
    <div class="buttons">
      <button @click="increment" data-test="increment">+</button>
      <button @click="decrement" data-test="decrement">-</button>
      <button @click="reset" data-test="reset">Reset</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useCounter } from '../composables/useCounter'

interface Props {
  initialValue?: number
}

const props = withDefaults(defineProps<Props>(), {
  initialValue: 0
})

const { count, increment, decrement, reset } = useCounter(props.initialValue)
</script>

<style scoped>
.counter {
  padding: 1rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  margin: 1rem 0;
  text-align: center;
}

.buttons {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
  margin-top: 1rem;
}

button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  background: #42b883;
  color: white;
  cursor: pointer;
  transition: background-color 0.2s;
}

button:hover {
  background: #369870;
}
</style>'''
    
    def _get_hello_world_component(self) -> str:
        """Generate HelloWorld component."""
        return '''<template>
  <div class="greetings">
    <h1 class="green">{{ msg }}</h1>
    <h3>
      You've successfully created a project with
      <a href="https://vitejs.dev/" target="_blank" rel="noopener">Vite</a> +
      <a href="https://vuejs.org/" target="_blank" rel="noopener">Vue 3</a> +
      <a href="https://www.typescriptlang.org/" target="_blank" rel="noopener">TypeScript</a>.
    </h3>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  msg: string
}>()
</script>

<style scoped>
h1 {
  font-weight: 500;
  font-size: 2.6rem;
  position: relative;
  top: -10px;
}

h3 {
  font-size: 1.2rem;
}

.greetings h1,
.greetings h3 {
  text-align: center;
}

@media (min-width: 1024px) {
  .greetings h1,
  .greetings h3 {
    text-align: left;
  }
}

.green {
  color: #42b883;
}
</style>'''
    
    def _get_use_counter_composable(self) -> str:
        """Generate useCounter composable."""
        return '''import { ref, readonly } from 'vue'

export function useCounter(initialValue = 0) {
  const count = ref(initialValue)

  const increment = () => {
    count.value++
  }

  const decrement = () => {
    count.value--
  }

  const reset = () => {
    count.value = initialValue
  }

  return {
    count: readonly(count),
    increment,
    decrement,
    reset
  }
}'''
    
    def _get_types(self) -> str:
        """Generate type definitions."""
        return '''// Common type definitions

export interface User {
  id: string
  name: string
  email: string
}

export interface ApiResponse<T> {
  data: T
  message?: string
  error?: string
}

export type Theme = 'light' | 'dark'
export type Status = 'idle' | 'loading' | 'success' | 'error'
'''
    
    def _get_constants(self) -> str:
        """Generate constants."""
        return '''// Application constants

export const APP_NAME = 'Vue SPA'
export const VERSION = '1.0.0'

export const API_ENDPOINTS = {
  USERS: '/api/users',
  AUTH: '/api/auth'
} as const

export const THEMES = {
  LIGHT: 'light',
  DARK: 'dark'
} as const
'''
    
    def _get_app_test(self) -> str:
        """Generate App test."""
        return '''import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import App from '../App.vue'

describe('App', () => {
  it('renders properly', () => {
    const wrapper = mount(App)
    expect(wrapper.text()).toContain('Vue 3 SPA')
  })

  it('contains HelloWorld component', () => {
    const wrapper = mount(App)
    expect(wrapper.findComponent({ name: 'HelloWorld' })).toBeTruthy()
  })

  it('contains Counter component', () => {
    const wrapper = mount(App)
    expect(wrapper.findComponent({ name: 'Counter' })).toBeTruthy()
  })
})'''
    
    def _get_counter_test(self) -> str:
        """Generate Counter test."""
        return '''import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import Counter from '../../components/Counter.vue'

describe('Counter', () => {
  it('renders with initial value', () => {
    const wrapper = mount(Counter, {
      props: { initialValue: 5 }
    })
    expect(wrapper.text()).toContain('Count: 5')
  })

  it('increments count when plus button clicked', async () => {
    const wrapper = mount(Counter, {
      props: { initialValue: 0 }
    })
    
    await wrapper.find('[data-test="increment"]').trigger('click')
    expect(wrapper.text()).toContain('Count: 1')
  })

  it('decrements count when minus button clicked', async () => {
    const wrapper = mount(Counter, {
      props: { initialValue: 5 }
    })
    
    await wrapper.find('[data-test="decrement"]').trigger('click')
    expect(wrapper.text()).toContain('Count: 4')
  })

  it('resets count when reset button clicked', async () => {
    const wrapper = mount(Counter, {
      props: { initialValue: 10 }
    })
    
    // Change the count first
    await wrapper.find('[data-test="increment"]').trigger('click')
    expect(wrapper.text()).toContain('Count: 11')
    
    // Then reset
    await wrapper.find('[data-test="reset"]').trigger('click')
    expect(wrapper.text()).toContain('Count: 10')
  })
})'''
    
    def _get_use_counter_test(self) -> str:
        """Generate useCounter composable test."""
        return '''import { describe, it, expect } from 'vitest'
import { useCounter } from '../../composables/useCounter'

describe('useCounter', () => {
  it('initializes with default value', () => {
    const { count } = useCounter()
    expect(count.value).toBe(0)
  })

  it('initializes with custom value', () => {
    const { count } = useCounter(10)
    expect(count.value).toBe(10)
  })

  it('increments count', () => {
    const { count, increment } = useCounter(5)
    increment()
    expect(count.value).toBe(6)
  })

  it('decrements count', () => {
    const { count, decrement } = useCounter(5)
    decrement()
    expect(count.value).toBe(4)
  })

  it('resets count to initial value', () => {
    const { count, increment, reset } = useCounter(8)
    increment()
    increment()
    expect(count.value).toBe(10)
    
    reset()
    expect(count.value).toBe(8)
  })
})'''
    
    def _get_test_setup(self) -> str:
        """Generate test setup."""
        return '''import { config } from '@vue/test-utils'

// Global test configuration
config.global.config.warnHandler = () => {}

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
  }),
})
'''
    
    def _get_vitest_config(self) -> str:
        """Generate Vitest configuration."""
        return '''import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/tests/setup.ts'],
    globals: true,
    exclude: ['**/node_modules/**', '**/dist/**', '**/cypress/**', '**/.{idea,git,cache,output,temp}/**', '**/tests/e2e/**'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        'src/tests/',
        '**/*.d.ts',
        '**/*.config.*',
        'dist/'
      ]
    }
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
})'''
    
    def _get_vitest_component_config(self) -> str:
        """Generate Vitest component configuration."""
        return '''import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/tests/setup.ts'],
    globals: true,
    include: ['src/tests/components/**/*.test.ts'],
    coverage: {
      include: ['src/components/**/*.vue']
    }
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
})'''
    
    def _get_playwright_config(self) -> str:
        """Generate Playwright configuration."""
        return '''import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:4173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],
  webServer: {
    command: 'npm run build && npm run preview',
    port: 4173,
    reuseExistingServer: !process.env.CI,
  },
})'''
    
    def _get_playwright_visual_config(self) -> str:
        """Generate Playwright visual regression configuration."""
        return '''import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/visual',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:4173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'npm run build && npm run preview',
    port: 4173,
    reuseExistingServer: !process.env.CI,
  },
})'''
    
    def _get_playwright_smoke_config(self) -> str:
        """Generate Playwright smoke test configuration."""
        return '''import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/smoke',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:4173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'npm run build && npm run preview',
    port: 4173,
    reuseExistingServer: !process.env.CI,
  },
})'''
    
    def _get_e2e_test(self) -> str:
        """Generate E2E test."""
        return '''import { test, expect } from '@playwright/test'

test('has title', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveTitle(/Vue SPA/)
})

test('counter functionality', async ({ page }) => {
  await page.goto('/')
  
  // Check initial state
  await expect(page.locator('[data-test="increment"]')).toBeVisible()
  
  // Test increment
  await page.click('[data-test="increment"]')
  await expect(page.locator('text=Count: 1')).toBeVisible()
  
  // Test decrement
  await page.click('[data-test="decrement"]')
  await expect(page.locator('text=Count: 0')).toBeVisible()
  
  // Test reset
  await page.click('[data-test="increment"]')
  await page.click('[data-test="increment"]')
  await expect(page.locator('text=Count: 2')).toBeVisible()
  
  await page.click('[data-test="reset"]')
  await expect(page.locator('text=Count: 0')).toBeVisible()
})'''