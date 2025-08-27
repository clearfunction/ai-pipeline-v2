"""
React SPA template generator using Vite + TypeScript.
Replicates the exact output of create-vite for React + TypeScript.
"""

from typing import List, Any
from templates.base_template_generator import BaseTemplateGenerator, GeneratedCode


class ReactSPATemplateGenerator(BaseTemplateGenerator):
    """Generates React SPA projects with Vite and TypeScript."""
    
    def __init__(self):
        super().__init__('react_spa')
    
    def generate_project_scaffold(self, project_name: str, architecture: Any) -> List[GeneratedCode]:
        """Generate complete React SPA project scaffold."""
        self.logger.info(f"Generating React SPA project: {project_name}")
        
        project_name = self._sanitize_project_name(project_name)
        generated_files = []
        
        # Generate all scaffold files
        templates = {
            'package.json': self._get_package_json(project_name),
            'vite.config.ts': self._get_vite_config(),
            'tsconfig.json': self._get_tsconfig(),
            'tsconfig.node.json': self._get_tsconfig_node(),
            'index.html': self._get_index_html(project_name),
            '.gitignore': self._get_gitignore(),
            'README.md': self._get_readme(project_name),
            'src/App.tsx': self._get_app_tsx(),
            'src/main.tsx': self._get_main_tsx(),
            'src/index.css': self._get_index_css(),
            'src/App.css': self._get_app_css(),
            'src/components/Counter.tsx': self._get_counter_component(),
            'src/hooks/useCounter.ts': self._get_use_counter_hook(),
            'src/types/index.ts': self._get_types(),
            'src/utils/constants.ts': self._get_constants(),
            'src/tests/App.test.tsx': self._get_app_test(),
            'src/tests/Counter.test.tsx': self._get_counter_test(),
            'src/tests/setup.ts': self._get_test_setup(),
            'vitest.config.ts': self._get_vitest_config()
        }
        
        for file_path, content in templates.items():
            generated_files.append(
                self._create_generated_code(file_path, content)
            )
        
        self.logger.info(f"Generated {len(generated_files)} React SPA files")
        return generated_files
    
    def get_supported_runtime(self) -> str:
        return 'node'
    
    def get_description(self) -> str:
        return 'React + Vite + TypeScript SPA with comprehensive testing'
    
    def _get_package_json(self, project_name: str) -> str:
        """Generate package.json with comprehensive test scripts."""
        return f'''{{
  "name": "{project_name}",
  "private": true,
  "version": "0.0.1",
  "type": "module",
  "scripts": {{
    "dev": "vite",
    "build": "tsc && vite build",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "preview": "vite preview",
    "test": "vitest run",
    "test:ci": "vitest run",
    "test:coverage": "vitest run --coverage",
    "test:watch": "vitest --watch",
    "type-check": "tsc --noEmit",
    "analyze:bundle": "npx vite-bundle-analyzer"
  }},
  "dependencies": {{
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  }},
  "devDependencies": {{
    "@types/react": "^18.2.66",
    "@types/react-dom": "^18.2.22",
    "@typescript-eslint/eslint-plugin": "^7.2.0",
    "@typescript-eslint/parser": "^7.2.0",
    "@vitejs/plugin-react": "^4.2.1",
    "eslint": "^8.57.0",
    "eslint-plugin-react-hooks": "^4.6.0",
    "eslint-plugin-react-refresh": "^0.4.6",
    "typescript": "^5.2.2",
    "vite": "^5.2.0",
    "vitest": "1.4.0",
    "@vitest/coverage-v8": "^1.4.0",
    "@testing-library/react": "14.2.1",
    "@testing-library/jest-dom": "6.4.2",
    "@testing-library/user-event": "14.5.2",
    "jsdom": "^24.0.0"
  }}
}}'''
    
    # Removed stub package-lock.json generation - will be created by npm install
    # def _get_package_lock_json(self, project_name: str) -> str:
    #     """Generate basic package-lock.json structure."""
    #     # This was causing npm ci failures because it didn't contain actual dependency resolution
    
    def _get_vite_config(self) -> str:
        """Generate Vite configuration."""
        return '''import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true
  },
  build: {
    outDir: 'build',
    sourcemap: true
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/tests/setup.ts',
  }
})'''
    
    def _get_tsconfig(self) -> str:
        """Generate TypeScript configuration."""
        return '''{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,

    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",

    /* Linting */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,

    /* Testing */
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}'''
    
    def _get_tsconfig_node(self) -> str:
        """Generate Node TypeScript configuration."""
        return '''{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}'''
    
    def _get_index_html(self, project_name: str) -> str:
        """Generate index.html."""
        return f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{project_name}</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
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
dist
dist-ssr
*.local

# Editor directories and files
.vscode/*
!.vscode/extensions.json
.idea
.DS_Store
*.suo
*.ntvs*
*.njsproj
*.sln
*.sw?

# Testing
coverage
.nyc_output

# Environment variables
.env
.env.local
.env.development.local
.env.test.local
.env.production.local'''
    
    def _get_readme(self, project_name: str) -> str:
        """Generate README.md."""
        return f'''# {project_name}

React SPA built with Vite and TypeScript.

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

# Run tests with coverage
npm run test:coverage
```

## Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run test` - Run tests in watch mode
- `npm run test:ci` - Run tests once
- `npm run test:coverage` - Run tests with coverage
- `npm run type-check` - Type checking
- `npm run lint` - Lint code
'''
    
    def _get_app_tsx(self) -> str:
        """Generate main App component."""
        return '''import { useState } from 'react'
import Counter from './components/Counter'
import './App.css'

function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="App">
      <header className="App-header">
        <h1>React SPA</h1>
        <p>Built with Vite and TypeScript</p>
        
        <Counter />
        
        <div className="card">
          <button onClick={() => setCount((count) => count + 1)}>
            App count is {count}
          </button>
        </div>
      </header>
    </div>
  )
}

export default App'''
    
    def _get_main_tsx(self) -> str:
        """Generate main.tsx entry point."""
        return '''import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)'''
    
    def _get_index_css(self) -> str:
        """Generate index.css."""
        return ''':root {
  font-family: Inter, system-ui, Avenir, Helvetica, Arial, sans-serif;
  line-height: 1.5;
  font-weight: 400;

  color-scheme: light dark;
  color: rgba(255, 255, 255, 0.87);
  background-color: #242424;

  font-synthesis: none;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  margin: 0;
  display: flex;
  place-items: center;
  min-width: 320px;
  min-height: 100vh;
}

#root {
  max-width: 1280px;
  margin: 0 auto;
  padding: 2rem;
  text-align: center;
}'''
    
    def _get_app_css(self) -> str:
        """Generate App.css."""
        return '''.App {
  text-align: center;
}

.App-header {
  background-color: #282c34;
  padding: 20px;
  color: white;
  border-radius: 8px;
}

.card {
  padding: 2em;
}

button {
  border-radius: 8px;
  border: 1px solid transparent;
  padding: 0.6em 1.2em;
  font-size: 1em;
  font-weight: 500;
  font-family: inherit;
  background-color: #1a1a1a;
  color: white;
  cursor: pointer;
  transition: border-color 0.25s;
}

button:hover {
  border-color: #646cff;
}

button:focus,
button:focus-visible {
  outline: 4px auto -webkit-focus-ring-color;
}'''
    
    def _get_counter_component(self) -> str:
        """Generate Counter component."""
        return '''import { useCounter } from '../hooks/useCounter'

interface CounterProps {
  initialValue?: number
}

export default function Counter({ initialValue = 0 }: CounterProps) {
  const { count, increment, decrement, reset } = useCounter(initialValue)

  return (
    <div className="counter">
      <h2>Counter Component</h2>
      <p>Count: {count}</p>
      <div>
        <button onClick={increment}>+</button>
        <button onClick={decrement}>-</button>
        <button onClick={reset}>Reset</button>
      </div>
    </div>
  )
}'''
    
    def _get_use_counter_hook(self) -> str:
        """Generate useCounter hook."""
        return '''import { useState, useCallback } from 'react'

export function useCounter(initialValue = 0) {
  const [count, setCount] = useState(initialValue)

  const increment = useCallback(() => {
    setCount(prev => prev + 1)
  }, [])

  const decrement = useCallback(() => {
    setCount(prev => prev - 1)
  }, [])

  const reset = useCallback(() => {
    setCount(initialValue)
  }, [initialValue])

  return {
    count,
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

export const APP_NAME = 'React SPA'
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
        return '''import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'
import App from '../App'

test('renders React SPA heading', () => {
  render(<App />)
  const heading = screen.getByText(/React SPA/i)
  expect(heading).toBeDefined()
})

test('renders counter component', () => {
  render(<App />)
  const counterHeading = screen.getByText(/Counter Component/i)
  expect(counterHeading).toBeDefined()
})'''
    
    def _get_counter_test(self) -> str:
        """Generate Counter test."""
        return '''import { render, screen, fireEvent } from '@testing-library/react'
import { expect, test } from 'vitest'
import Counter from '../components/Counter'

test('renders counter with initial value', () => {
  render(<Counter initialValue={5} />)
  expect(screen.getByText('Count: 5')).toBeDefined()
})

test('increments count when plus button clicked', () => {
  render(<Counter initialValue={0} />)
  const incrementButton = screen.getByText('+')
  fireEvent.click(incrementButton)
  expect(screen.getByText('Count: 1')).toBeDefined()
})

test('decrements count when minus button clicked', () => {
  render(<Counter initialValue={5} />)
  const decrementButton = screen.getByText('-')
  fireEvent.click(decrementButton)
  expect(screen.getByText('Count: 4')).toBeDefined()
})

test('resets count when reset button clicked', () => {
  render(<Counter initialValue={10} />)
  const resetButton = screen.getByText('Reset')
  fireEvent.click(resetButton)
  expect(screen.getByText('Count: 10')).toBeDefined()
})'''
    
    def _get_test_setup(self) -> str:
        """Generate test setup."""
        return '''import '@testing-library/jest-dom'

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
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/tests/setup.ts'],
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
  }
})'''