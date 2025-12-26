'use client'

import { useState, useEffect } from 'react'

export default function LcarsHeader() {
    const [time, setTime] = useState(new Date())

    const [mounted, setMounted] = useState(false)

    useEffect(() => {
        setMounted(true)
        const timer = setInterval(() => setTime(new Date()), 1000)
        return () => clearInterval(timer)
    }, [])

    const formatTime = (date: Date) => {
        if (!mounted) return '00:00:00'
        return date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        })
    }

    const formatDate = (date: Date) => {
        if (!mounted) return 'LOADING...'
        const days = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
        const day = days[date.getDay()]
        const dateStr = String(date.getDate()).padStart(2, '0')
        const month = String(date.getMonth() + 1).padStart(2, '0')
        const year = date.getFullYear()
        return `${day} • ${dateStr}.${month}.${year}`
    }

    return (
        <div className="w-full flex flex-col gap-1 shrink-0">
            {/* Top Cap Bar */}
            <div className="flex items-end h-16 w-full">

                {/* Left: Clock Module */}
                <div className="w-64 bg-lcars-orange h-full rounded-tr-[30px] rounded-bl-[30px] flex flex-col justify-center px-6 relative mr-2">
                    <div className="text-black font-antonio font-bold text-4xl tracking-widest leading-none">
                        {formatTime(time)}
                    </div>
                    <div className="text-black font-bold text-xs tracking-[0.2em] mt-1 opacity-80">
                        {formatDate(time)}
                    </div>
                </div>

                {/* Center: Title Bar */}
                <div className="flex-1 flex items-end h-full mx-2">
                    {/* Decorative segments */}
                    <div className="h-8 w-16 bg-lcars-gold rounded-full mr-2 mb-4 opacity-80"></div>
                    <div className="h-8 w-8 bg-lcars-lavender rounded-full mr-2 mb-4 opacity-60"></div>

                    {/* Main Title Block */}
                    <div className="flex-1 bg-lcars-orange/10 border-t-4 border-b-4 border-lcars-orange h-12 mb-2 rounded-full flex items-center justify-center relative">
                        <h1 className="text-lcars-orange font-antonio font-bold text-3xl tracking-[0.3em] text-glow uppercase">
                            DemestiChat
                        </h1>
                        {/* Tiny decorative ticks */}
                        <div className="absolute top-0 left-10 w-1 h-2 bg-lcars-orange"></div>
                        <div className="absolute bottom-0 right-10 w-1 h-2 bg-lcars-orange"></div>
                    </div>

                    {/* Right decorative segments */}
                    <div className="h-8 w-8 bg-lcars-blue rounded-full ml-2 mb-4 opacity-60"></div>
                    <div className="h-8 w-16 bg-lcars-gold rounded-full ml-2 mb-4 opacity-80"></div>
                </div>

                {/* Right: User & Status */}
                <div className="w-80 flex flex-col items-end justify-end h-full">
                    <div className="flex gap-2 mb-2">
                        <div className="bg-lcars-green/20 text-lcars-green border border-lcars-green px-4 py-1 rounded-full text-[10px] font-bold tracking-widest animate-pulse">
                            ONLINE
                        </div>
                        <div className="bg-lcars-blue/20 text-lcars-blue border border-lcars-blue px-4 py-1 rounded-full text-[10px] font-bold tracking-widest">
                            SECURE
                        </div>
                    </div>

                    {/* User Bar */}
                    <div className="w-full bg-lcars-lavender h-10 rounded-tl-[20px] rounded-br-[20px] flex items-center justify-between px-4">
                        <span className="text-black font-bold text-xs tracking-widest">USER: EXECUTIVE_MENE</span>
                        <span className="bg-black/20 px-2 py-0.5 rounded text-[9px] font-bold text-black">SETTINGS</span>
                    </div>
                </div>
            </div>

            {/* Horizontal Separator Line (The "Neck") */}
            <div className="w-full h-2 bg-lcars-gold rounded-full opacity-50"></div>
        </div>
    )
}
