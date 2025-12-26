/** @type {import('next').NextConfig} */
const nextConfig = {
    async rewrites() {
        return [
            {
                source: '/api/:path*',
                destination: 'http://agent:8000/:path*', // Proxy to backend service in Docker
            },
        ]
    },
    allowedDevOrigins: [
        'demestichat.beltlineconsulting.co',
        '178.156.170.161'
    ],
}

module.exports = nextConfig
