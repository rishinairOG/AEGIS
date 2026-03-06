/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            fontFamily: {
                mono: ['"Share Tech Mono"', 'monospace'],
                display: ['Orbitron', 'sans-serif'],
            },
            colors: {
                cyan: {
                    400: '#22d3ee',
                    500: '#06b6d4',
                    900: '#164e63',
                },
                accent: {
                    amber: '#f59e0b',
                    magenta: '#d946ef',
                },
            },
            animation: {
                'pulse-soft': 'pulse-soft 2s ease-in-out infinite',
            },
            keyframes: {
                'pulse-soft': {
                    '0%, 100%': { opacity: '1' },
                    '50%': { opacity: '0.7' },
                },
            },
        },
    },
    plugins: [],
}
