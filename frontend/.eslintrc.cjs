module.exports = {
  root: true,
  env: {
    browser: true,
    es2021: true,
    node: true,
  },
  extends: [
    'eslint:recommended',
    'plugin:react/recommended',
    'plugin:react/jsx-runtime',
    'plugin:react-hooks/recommended',
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    ecmaFeatures: {
      jsx: true,
    },
  },
  settings: {
    react: {
      version: 'detect',
    },
  },
  plugins: ['react', 'react-hooks', 'react-refresh'],
  rules: {
    // React rules
    'react/prop-types': 'off', // We use TypeScript/JSDoc for prop validation
    'react/react-in-jsx-scope': 'off', // Not needed in React 17+
    'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],

    // Code quality
    'no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
    'no-console': ['warn', { allow: ['warn', 'error'] }],
    'no-debugger': 'warn',

    // Best practices
    'no-undef': 'error', // Catch undefined variables (like API_BASE_URL)
    'prefer-const': 'warn',
    'no-var': 'error',

    // Prevent common errors
    'no-constant-condition': 'warn',
    'no-dupe-keys': 'error',
    'no-duplicate-case': 'error',
    'no-unreachable': 'warn',

    // Stylistic
    'quotes': ['warn', 'double', { avoidEscape: true }],
    'semi': ['warn', 'always'],
  },
  ignorePatterns: ['dist', 'node_modules', '*.config.js', '*.config.cjs'],
};
