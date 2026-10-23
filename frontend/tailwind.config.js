/** Design tokens from design/design_system.md (Stitch "SachVerify Minimal"). */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: { DEFAULT: '#171717', 2: '#525252', 3: '#A3A3A3' },
        line: '#E5E5E5',
        subtle: '#FAFAFA',
        accent: { DEFAULT: '#0F766E', hover: '#115E59' },
        st: { verified: '#5F7F68', conflicting: '#A88442', outdated: '#A3A3A3', unverified: '#6B7A99', alert: '#9C4F3A' },
      },
      fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'], mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'] },
    },
  },
  plugins: [],
}
