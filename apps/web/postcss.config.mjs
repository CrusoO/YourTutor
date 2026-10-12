// Tailwind runs in utilities-only mode (no preflight reset): the legacy stylesheet keeps working.
const config = { plugins: { "@tailwindcss/postcss": {} } };
export default config;
