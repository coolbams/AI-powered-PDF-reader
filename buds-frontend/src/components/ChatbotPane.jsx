import { Textarea } from "./ui/textarea";

// This is the right-side chat panel.
// It is meant to hold the user prompt and eventually send it to the backend.
export default function ChatbotPane({ activeDoc }) {
    return (
        <>
            <div className="flex flex-col w-full h-full rounded-2xl px-4 py-5 bg-[#1F1F1F]" id="ChatBot Container">

                <div className="w-full h-full relative min-h-75 pb-12.5">
                    {/* The chat input sits at the bottom of the panel */}
                    <div className="absolute bottom-0 left-0 w-full max-h-15 outline-none border-none">
                        <Textarea
                            placeholder="Ask me ..."
                            className="max-h-15 outline-none border-none text-white text-3xl "
                        />
                    </div>
                </div>

            </div>
        </>
    )
}