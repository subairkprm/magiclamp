/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#f0f4ff',
          100: '#dce6fd',
          200: '#b9ccfb',
          300: '#8aaaf7',
          400: '#6188f2',
          500: '#4166ec',
          600: '#2e4fe0',
          700: '#253ccc',
          800: '#2232a5',
          900: '#212e82',
          950: '#161d51',
        },
      },
    },
  },
  plugins: [],
}
