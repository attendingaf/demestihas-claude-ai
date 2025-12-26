'use client'

export default function LcarsSidebar() {
    return (
        <div className="w-64 h-full flex flex-col shrink-0 pt-4 pb-4">
            {/* Top Button */}
            <button className="h-12 bg-lcars-orange hover:bg-lcars-orange-light text-black font-antonio font-bold text-xl tracking-widest rounded-r-full mb-4 ml-2 transition-colors text-left pl-6">
                NEW CHAT
            </button>

            {/* Main Control Column with Sweeping Curve */}
            <div className="flex-1 flex relative">
                {/* The Vertical Bar */}
                <div className="w-32 bg-lcars-gold h-full flex flex-col items-end py-4 gap-1 relative rounded-bl-[40px]">

                    {/* The Sweeping Curve (Negative Space) */}
                    <div className="absolute top-0 right-[-32px] w-32 h-64 bg-lcars-gold rounded-tr-[100px] -z-10"></div>
                    {/* Black cutout to define the curve */}
                    <div className="absolute top-0 right-[-32px] w-32 h-64 bg-black rounded-bl-[60px] z-0"></div>

                    {/* Content inside the bar */}
                    <div className="w-full flex flex-col gap-4 px-2 z-10 mt-8">

                        {/* Group 1: History */}
                        <div className="flex flex-col gap-1">
                            <div className="text-black text-[10px] font-bold text-right pr-2 mb-1 opacity-70">CHAT HISTORY</div>
                            <div className="h-8 bg-lcars-orange-dim rounded-full w-full mb-1"></div>
                            <div className="h-8 bg-lcars-blue-dim rounded-full w-full mb-1"></div>
                            <div className="h-8 bg-lcars-lavender-dim rounded-full w-full"></div>
                        </div>

                        {/* Separator */}
                        <div className="h-1 bg-black/30 w-full my-2"></div>

                        {/* Group 2: Projects/Artifacts (spacer preserved for curve visibility) */}
                        <div className="flex flex-col gap-1">
                            <div className="h-[14px] mb-1"></div>
                            <button className="h-8 bg-lcars-blue hover:bg-lcars-blue-light rounded-full w-full text-right pr-3 text-[10px] font-bold text-black uppercase">Projects</button>
                            <button className="h-8 bg-lcars-blue hover:bg-lcars-blue-light rounded-full w-full text-right pr-3 text-[10px] font-bold text-black uppercase">Artifacts</button>
                        </div>

                        {/* Separator */}
                        <div className="h-1 bg-black/30 w-full my-2"></div>

                        {/* Group 3: Actions */}
                        <div className="flex flex-col gap-1">
                            <div className="text-black text-[10px] font-bold text-right pr-2 mb-1 opacity-70">ACTIONS</div>
                            <button className="h-8 bg-lcars-lavender hover:bg-lcars-lavender-light rounded-full w-full text-right pr-3 text-[10px] font-bold text-black uppercase">Upload</button>
                            <button className="h-8 bg-lcars-lavender hover:bg-lcars-lavender-light rounded-full w-full text-right pr-3 text-[10px] font-bold text-black uppercase">Starred</button>
                        </div>

                        {/* Filler Data Pads */}
                        <div className="flex-1 flex flex-col justify-end gap-1 mt-4 opacity-80">
                            <div className="h-4 bg-lcars-gold-dim rounded-full w-3/4 self-end"></div>
                            <div className="h-4 bg-lcars-gold-dim rounded-full w-1/2 self-end"></div>
                            <div className="h-4 bg-lcars-gold-dim rounded-full w-full"></div>
                        </div>

                    </div>
                </div>

                {/* The "Elbow" Connection to Content Frame */}
                <div className="flex-1 relative">
                    {/* This space is left empty for the main content to "fit" into */}
                </div>
            </div>

            {/* Bottom Cap */}
            <div className="h-16 w-48 bg-lcars-gold rounded-br-[50px] mt-1 relative">
                <div className="absolute bottom-4 left-4 text-black font-bold text-xs tracking-widest">LCARS 47</div>
            </div>
        </div>
    )
}
