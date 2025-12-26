'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import axios from 'axios'

export default function LoginPage() {
    const [userId, setUserId] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState<string>('')
    const [isLoading, setIsLoading] = useState(false)
    const router = useRouter()

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')
        setIsLoading(true)

        try {
            const response = await axios.post(`/api/auth/login?user_id=${encodeURIComponent(userId)}&password=${encodeURIComponent(password)}`)

            // Store the token
            localStorage.setItem('jwt_token', response.data.access_token)
            localStorage.setItem('user_id', userId)

            // Redirect to chat
            router.push('/')
        } catch (err: any) {
            const detail = err?.response?.data?.detail;
            const message =
                typeof detail === 'string'
                    ? detail
                    : detail?.msg ||
                    (detail ? JSON.stringify(detail) : undefined) ||
                    'Login failed. Please try again.';
            setError(message);
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="h-screen w-screen bg-black flex items-center justify-center p-4">
            <div className="w-full max-w-md">

                {/* LCARS Header */}
                <div className="mb-8 text-center">
                    <div className="text-lcars-orange text-6xl font-antonio font-bold tracking-widest mb-2">
                        LCARS 24
                    </div>
                    <div className="text-lcars-gold text-lg tracking-[0.3em]">
                        AUTHENTICATION REQUIRED
                    </div>
                </div>

                {/* Login Form */}
                <form onSubmit={handleLogin} className="space-y-6">

                    {/* User ID Field */}
                    <div>
                        <label className="block text-lcars-orange text-sm font-bold tracking-widest mb-2">
                            USER ID
                        </label>
                        <input
                            type="text"
                            value={userId}
                            onChange={(e) => setUserId(e.target.value)}
                            className="w-full bg-black border-2 border-lcars-orange rounded-full px-6 py-3 text-lcars-orange font-antonio text-lg tracking-wider focus:outline-none focus:shadow-[0_0_30px_rgba(255,156,40,0.4)] transition-all placeholder-lcars-orange/30"
                            placeholder="Enter user ID..."
                            required
                            disabled={isLoading}
                        />
                    </div>

                    {/* Password Field */}
                    <div>
                        <label className="block text-lcars-orange text-sm font-bold tracking-widest mb-2">
                            PASSWORD
                        </label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full bg-black border-2 border-lcars-orange rounded-full px-6 py-3 text-lcars-orange font-antonio text-lg tracking-wider focus:outline-none focus:shadow-[0_0_30px_rgba(255,156,40,0.4)] transition-all placeholder-lcars-orange/30"
                            placeholder="Enter password..."
                            required
                            disabled={isLoading}
                        />
                    </div>

                    {/* Error Message */}
                    {error && (
                        <div className="bg-lcars-red/20 border-2 border-lcars-red rounded-[20px] p-4 text-lcars-red text-sm font-bold tracking-wide">
                            ⚠ {String(error)}
                        </div>
                    )}

                    {/* Submit Button */}
                    <button
                        type="submit"
                        disabled={isLoading}
                        className="w-full bg-lcars-orange hover:bg-lcars-orange-light text-black font-antonio font-bold text-xl tracking-widest py-4 rounded-full transition-all hover:scale-105 active:scale-95 disabled:opacity-50 disabled:hover:scale-100"
                    >
                        {isLoading ? 'AUTHENTICATING...' : 'ENGAGE'}
                    </button>

                </form>

                {/* Decorative Elements */}
                <div className="mt-8 flex items-center justify-center gap-2">
                    <div className="h-1 w-16 bg-lcars-orange rounded-full"></div>
                    <div className="h-1 w-8 bg-lcars-gold rounded-full"></div>
                    <div className="h-1 w-16 bg-lcars-lavender rounded-full"></div>
                </div>

            </div>
        </div>
    )
}
