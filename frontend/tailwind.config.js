/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{ts,js,html}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: 'var(--sl-color-primary-50)',
          100: 'var(--sl-color-primary-100)',
          200: 'var(--sl-color-primary-200)',
          300: 'var(--sl-color-primary-300)',
          400: 'var(--sl-color-primary-400)',
          500: 'var(--sl-color-primary-500)',
          600: 'var(--sl-color-primary-600)',
          700: 'var(--sl-color-primary-700)',
          800: 'var(--sl-color-primary-800)',
          900: 'var(--sl-color-primary-900)',
        },
        neutral: {
          0: 'var(--sl-color-neutral-0)',
          50: 'var(--sl-color-neutral-50)',
          100: 'var(--sl-color-neutral-100)',
          200: 'var(--sl-color-neutral-200)',
          300: 'var(--sl-color-neutral-300)',
          400: 'var(--sl-color-neutral-400)',
          500: 'var(--sl-color-neutral-500)',
          600: 'var(--sl-color-neutral-600)',
          700: 'var(--sl-color-neutral-700)',
          800: 'var(--sl-color-neutral-800)',
          900: 'var(--sl-color-neutral-900)',
          1000: 'var(--sl-color-neutral-1000)',
        },
      },
    },
  },
  plugins: [],
};
