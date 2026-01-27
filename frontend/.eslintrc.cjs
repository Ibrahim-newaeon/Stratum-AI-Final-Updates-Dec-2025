// =============================================================================
// Stratum AI - ESLint Configuration
// =============================================================================
// Strict linting for TypeScript React codebase

module.exports = {
  root: true,
  env: {
    browser: true,
    es2022: true,
    node: true,
  },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:@typescript-eslint/recommended-requiring-type-checking',
    'plugin:react/recommended',
    'plugin:react/jsx-runtime',
    'plugin:react-hooks/recommended',
  ],
  ignorePatterns: [
    'dist',
    'node_modules',
    '.eslintrc.cjs',
    'vite.config.ts',
    'tailwind.config.js',
    'postcss.config.js',
    '*.d.ts',
  ],
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    project: ['./tsconfig.json', './tsconfig.node.json'],
    tsconfigRootDir: __dirname,
    ecmaFeatures: {
      jsx: true,
    },
  },
  plugins: ['react', 'react-refresh', '@typescript-eslint'],
  settings: {
    react: {
      version: 'detect',
    },
  },
  rules: {
    // ==========================================================================
    // React Rules
    // ==========================================================================
    'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
    'react/prop-types': 'off', // TypeScript handles this
    'react/no-unescaped-entities': 'warn',
    'react/jsx-no-target-blank': 'error',
    'react/jsx-curly-brace-presence': ['warn', { props: 'never', children: 'never' }],
    'react/self-closing-comp': 'warn',

    // ==========================================================================
    // TypeScript Rules
    // ==========================================================================
    '@typescript-eslint/no-unused-vars': [
      'warn',
      {
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^_',
        caughtErrorsIgnorePattern: '^_',
      },
    ],
    '@typescript-eslint/no-explicit-any': 'off', // Relaxed for legacy code
    '@typescript-eslint/no-unsafe-assignment': 'off', // Relaxed for legacy code
    '@typescript-eslint/no-unsafe-member-access': 'off', // Relaxed for legacy code
    '@typescript-eslint/no-unsafe-call': 'off', // Relaxed for legacy code
    '@typescript-eslint/no-unsafe-argument': 'off', // Relaxed for legacy code
    '@typescript-eslint/no-unsafe-return': 'off', // Relaxed for legacy code
    '@typescript-eslint/explicit-function-return-type': 'off',
    '@typescript-eslint/explicit-module-boundary-types': 'off',
    '@typescript-eslint/no-non-null-assertion': 'warn',
    '@typescript-eslint/no-floating-promises': 'warn', // Relaxed for initial setup
    '@typescript-eslint/no-misused-promises': 'off', // Relaxed for initial setup
    '@typescript-eslint/await-thenable': 'warn', // Relaxed for initial setup
    '@typescript-eslint/require-await': 'off', // Relaxed - too many false positives
    '@typescript-eslint/no-unnecessary-type-assertion': 'warn',
    '@typescript-eslint/restrict-template-expressions': 'off', // Relaxed for legacy code

    // ==========================================================================
    // General Rules
    // ==========================================================================
    'no-console': ['warn', { allow: ['warn', 'error'] }],
    'no-debugger': 'warn',
    'no-alert': 'warn',
    'prefer-const': 'warn',
    'no-var': 'error',
    eqeqeq: ['error', 'always', { null: 'ignore' }],
    curly: ['warn', 'multi-line'],
    'no-throw-literal': 'error',
    'prefer-promise-reject-errors': 'error',
    'no-return-await': 'warn',
    'no-await-in-loop': 'warn',

    // ==========================================================================
    // Import Rules
    // ==========================================================================
    'sort-imports': [
      'warn',
      {
        ignoreCase: true,
        ignoreDeclarationSort: true,
        ignoreMemberSort: false,
      },
    ],
  },
  overrides: [
    // Test files
    {
      files: ['**/*.test.ts', '**/*.test.tsx', '**/*.spec.ts', '**/*.spec.tsx'],
      env: {
        jest: true,
      },
      rules: {
        '@typescript-eslint/no-explicit-any': 'off',
        '@typescript-eslint/no-non-null-assertion': 'off',
        'no-console': 'off',
      },
    },
    // Config files
    {
      files: ['*.config.ts', '*.config.js'],
      rules: {
        '@typescript-eslint/no-var-requires': 'off',
      },
    },
  ],
};
