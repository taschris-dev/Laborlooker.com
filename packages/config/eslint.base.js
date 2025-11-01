module.exports = {
  root: true,
  extends: [
    "@next/eslint-config-next",
    "eslint:recommended",
    "@typescript-eslint/recommended",
    "prettier"
  ],
  parser: "@typescript-eslint/parser",
  plugins: ["@typescript-eslint"],
  rules: {
    "@typescript-eslint/no-unused-vars": ["error", { "argsIgnorePattern": "^_" }],
    "@typescript-eslint/no-explicit-any": "warn",
    "prefer-const": "error",
    "no-var": "error"
  },
  overrides: [
    {
      files: ["*.config.js", "*.config.ts"],
      env: {
        node: true
      }
    }
  ]
};