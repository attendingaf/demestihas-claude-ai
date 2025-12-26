/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
        './src/components/**/*.{js,ts,jsx,tsx,mdx}',
        './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    theme: {
        extend: {
            colors: {
                lcars: {
                    orange: {
                        DEFAULT: '#FF9C28', // Deep Orange
                        dim: '#CC7D20',
                        light: '#FFB050'
                    },
                    gold: {
                        DEFAULT: '#FFD185', // Muted Gold
                        dim: '#CCA76A',
                        light: '#FFE0A3'
                    },
                    lavender: {
                        DEFAULT: '#C7A1E3', // Distinct Lavender
                        dim: '#9F80B5',
                        light: '#DBC2F0'
                    },
                    blue: {
                        DEFAULT: '#8F8FFF', // Tactical Blue
                        dim: '#7272CC',
                        light: '#B0B0FF'
                    },
                    red: {
                        DEFAULT: '#D65050', // Alert Red
                        dim: '#AB4040'
                    },
                    black: '#000000',
                    gray: '#111111'
                },
            },
            fontFamily: {
                antonio: ['Antonio', 'sans-serif'],
                system: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Helvetica Neue', 'Arial', 'sans-serif'],
            },
            backgroundImage: {
                'lcars-curve-top-left': 'radial-gradient(circle at 100% 100%, transparent 40px, #FF9C28 41px)',
            }
        },
    },
    plugins: [],
}
