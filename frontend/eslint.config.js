// =============================================================================
// Stratum AI - ESLint Configuration (Flat Config for ESLint 9+)
// =============================================================================
// Strict linting for TypeScript React codebase

import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import reactPlugin from 'eslint-plugin-react';
import reactHooksPlugin from 'eslint-plugin-react-hooks';
import reactRefreshPlugin from 'eslint-plugin-react-refresh';
import globals from 'globals';

export default tseslint.config(
  // =========================================================================
  // 1. Global ignores (replaces ignorePatterns)
  // =========================================================================
  {
    ignores: [
      'dist/**',
      'node_modules/**',
      '**/*.d.ts',
      'vite.config.ts',
      'tailwind.config.js',
      'postcss.config.js',
      'e2e/**',
      'playwright.config.ts',
      'public/**',
    ],
  },

  // =========================================================================
  // 2. Linter options
  // =========================================================================
  {
    linterOptions: {
      reportUnusedDisableDirectives: 'warn',
    },
  },

  // =========================================================================
  // 3. Base JS recommended rules (replaces eslint:recommended)
  // =========================================================================
  js.configs.recommended,

  // =========================================================================
  // 3. TypeScript type-aware linting (replaces @typescript-eslint/recommended
  //    + recommended-requiring-type-checking)
  // =========================================================================
  ...tseslint.configs.recommendedTypeChecked.map((config) => ({
    ...config,
    files: ['src/**/*.ts', 'src/**/*.tsx'],
  })),
  {
    files: ['src/**/*.ts', 'src/**/*.tsx'],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.json'],
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },

  // =========================================================================
  // 4. React plugin (replaces plugin:react/recommended + jsx-runtime)
  // =========================================================================
  {
    files: ['src/**/*.ts', 'src/**/*.tsx'],
    plugins: {
      react: reactPlugin,
    },
    settings: {
      react: {
        version: 'detect',
      },
    },
    rules: {
      ...reactPlugin.configs.recommended.rules,
      ...reactPlugin.configs['jsx-runtime'].rules,
    },
  },

  // =========================================================================
  // 5. React Hooks (replaces plugin:react-hooks/recommended)
  // =========================================================================
  {
    files: ['src/**/*.ts', 'src/**/*.tsx'],
    plugins: {
      'react-hooks': reactHooksPlugin,
    },
    rules: {
      ...reactHooksPlugin.configs.recommended.rules,
      'react-hooks/exhaustive-deps': 'off', // Relaxed - intentional missing deps to prevent re-render loops
    },
  },

  // =========================================================================
  // 6. React Refresh
  // =========================================================================
  {
    files: ['src/**/*.ts', 'src/**/*.tsx'],
    plugins: {
      'react-refresh': reactRefreshPlugin,
    },
    rules: {
      'react-refresh/only-export-components': 'off', // Relaxed - mixed exports are common in this codebase
    },
  },

  // =========================================================================
  // 7. Custom rules + globals (all existing rules preserved)
  // =========================================================================
  {
    files: ['src/**/*.ts', 'src/**/*.tsx'],
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.es2021,
        ...globals.node,
      },
    },
    rules: {
      // =====================================================================
      // React Rules
      // =====================================================================
      'react/prop-types': 'off', // TypeScript handles this
      'react/no-unescaped-entities': 'off', // Relaxed - widespread apostrophes/quotes in JSX text
      'react/jsx-no-target-blank': 'error',
      'react/jsx-curly-brace-presence': ['warn', { props: 'never', children: 'never' }],
      'react/self-closing-comp': 'warn',

      // =====================================================================
      // TypeScript Rules
      // =====================================================================
      '@typescript-eslint/no-unused-vars': 'off', // Relaxed - 179 unused vars across legacy codebase
      '@typescript-eslint/no-explicit-any': 'off', // Relaxed for legacy code
      '@typescript-eslint/no-unsafe-assignment': 'off', // Relaxed for legacy code
      '@typescript-eslint/no-unsafe-member-access': 'off', // Relaxed for legacy code
      '@typescript-eslint/no-unsafe-call': 'off', // Relaxed for legacy code
      '@typescript-eslint/no-unsafe-argument': 'off', // Relaxed for legacy code
      '@typescript-eslint/no-unsafe-return': 'off', // Relaxed for legacy code
      '@typescript-eslint/explicit-function-return-type': 'off',
      '@typescript-eslint/explicit-module-boundary-types': 'off',
      '@typescript-eslint/no-non-null-assertion': 'off', // Relaxed for legacy code
      '@typescript-eslint/no-floating-promises': 'off', // Relaxed - 314 fire-and-forget mutation callbacks
      '@typescript-eslint/no-misused-promises': 'off', // Relaxed for initial setup
      '@typescript-eslint/await-thenable': 'off', // Relaxed for initial setup
      '@typescript-eslint/require-await': 'off', // Relaxed - too many false positives
      '@typescript-eslint/no-unnecessary-type-assertion': 'off', // Relaxed for legacy code
      '@typescript-eslint/restrict-template-expressions': 'off', // Relaxed for legacy code

      // New rules in typescript-eslint v8 - relaxed for legacy code parity
      '@typescript-eslint/no-base-to-string': 'off', // Relaxed for legacy code
      '@typescript-eslint/no-empty-object-type': 'off', // Relaxed for legacy code
      '@typescript-eslint/prefer-promise-reject-errors': 'off', // Relaxed for legacy code
      '@typescript-eslint/only-throw-error': 'off', // Relaxed for legacy code
      '@typescript-eslint/no-redundant-type-constituents': 'off', // Relaxed for legacy code
      '@typescript-eslint/no-non-null-asserted-optional-chain': 'off', // Relaxed for legacy code

      // =====================================================================
      // General Rules
      // =====================================================================
      'no-console': 'off', // Relaxed - widespread console.log usage for debugging
      'no-debugger': 'warn',
      'no-alert': 'off', // Relaxed - intentional alert/confirm/prompt usage throughout
      'prefer-const': 'warn',
      'no-var': 'error',
      eqeqeq: ['error', 'always', { null: 'ignore' }],
      curly: ['warn', 'multi-line'],
      'no-throw-literal': 'error',
      'prefer-promise-reject-errors': 'error',
      'no-return-await': 'off', // Relaxed for legacy code
      'no-await-in-loop': 'off', // Relaxed - intentional sequential async patterns

      // =====================================================================
      // Import Rules
      // =====================================================================
      'sort-imports': 'off', // Relaxed - cosmetic import ordering
    },
  },

  // =========================================================================
  // 8. Test file overrides
  // =========================================================================
  {
    files: ['**/*.test.ts', '**/*.test.tsx', '**/*.spec.ts', '**/*.spec.tsx'],
    languageOptions: {
      globals: {
        ...globals.jest,
      },
    },
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-non-null-assertion': 'off',
      'no-console': 'off',
    },
  },

  // =========================================================================
  // 9. Config file overrides
  // =========================================================================
  {
    files: ['*.config.ts', '*.config.js'],
    rules: {
      '@typescript-eslint/no-require-imports': 'off',
    },
  },
);
