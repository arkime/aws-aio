/* eslint-env node */
module.exports = {
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended-type-checked'
  ],
  parser: '@typescript-eslint/parser',
  plugins: ['@typescript-eslint'],
  parserOptions: {
    project: true,
    tsconfigRootDir: __dirname,
  },
  root: true,
  rules: {

    // Arkime rules
    'generator-star-spacing': 'off',
    'semi': ['error', 'always'],
    'handle-callback-err': ['error', 'never'],
    'prefer-promise-reject-errors': 0,
    'no-labels': ['error', { 'allowLoop': true }],
    'no-new-func': 'off',
    'indent': ['error', 4, {'SwitchCase': 0}],
    'no-useless-return': 'off',
    'no-empty': 'off',
    'default-case-last': 'off',

     // TODO - reenable below at some point
    "@typescript-eslint/no-unsafe-assignment": "off",
    "@typescript-eslint/restrict-template-expressions": "off",
  },
};
