
'use client'
import React from 'react'
import { TextGenerateEffect } from "@/components/ui/text-generate-effect";
import { BackgroundBeams } from "@/components/ui/BackgroundBeams";

const pointsData: string[] = [
  "Personalized EQ Assessment: Our platform begins with a comprehensive evaluation of the user's emotional intelligence, identifying strengths and areas for growth.",
  "Daily Emotional Check-ins: Users engage in brief, daily check-ins that capture their emotional states, providing real-time data for analysis.",
  "Interactive Journaling: The platform encourages reflective journaling, helping users articulate their feelings and experiences.",
  "AI-Powered Insights: Advanced algorithms analyze emotional data to identify patterns and provide personalized insights.",
  "Tailored Improvement Plans: Based on the analysis, users receive customized exercises and strategies to enhance their emotional intelligence.",
  "Progress Tracking: Users can monitor their emotional growth over time through visual dashboards and reports."
];

function Learnmore() {
    return (
        <div className="relative min-h-screen w-full flex flex-col items-center justify-center p-4 antialiased">
            <div className="max-w-6xl mx-auto px-8 w-full mt-24">
                <TextGenerateEffect
                    words="The Ra.AI Solution"
                    duration={0.6}
                    filter={true}
                    className='text-left text-4xl sm:text-5xl font-bold mb-8'
                />
                <TextGenerateEffect
                    words="Ra.AI is a personalized emotional intelligence platform designed to empower individuals by helping them understand, track, and improve their emotional well-being. Unlike generic wellness apps, Ra.AI uses a dynamic and adaptive approach to assess a user's Emotional Quotient (EQ) levels and provide a deeply personalized experience. Through a series of intelligent daily check-ins and interactive journaling, the platform tracks emotional patterns over time, providing users with a visual and data-driven understanding of their emotional triggers and states. Our core innovation lies in a proprietary EQ assessment model that, combined with AI-powered analysis, generates a tailored curriculum of exercises and insights. These aren't one-size-fits-all suggestions; they are unique, actionable steps designed to improve an individual's self-awareness, emotional regulation, motivation, and interpersonal skills. Ra.AI is your personal guide to building a more resilient, empathetic, and emotionally intelligent self."
                    duration={0.6}
                    filter={true}
                    className='font-light text-base md:text-lg lg:text-xl text-left'
                />
                <hr className="my-16 border-gray-700" />
                <TextGenerateEffect
                    words="Key Points of Our Solution"
                    duration={0.6}
                    filter={true}
                    className='text-center text-3xl sm:text-4xl font-semibold mb-8'
                />
                <ul className="space-y-8">
                    {pointsData.map((point, index) => (
                        <li key={index} className="flex items-start">
                            <span className="font-bold text-lg mr-2 text-white">{index + 1}.</span>
                            <TextGenerateEffect
                                words={point}
                                duration={0.6}
                                filter={true}
                                className='font-light text-base md:text-lg lg:text-xl'
                            />
                        </li>
                    ))}
                </ul>
            </div>
            <BackgroundBeams className="absolute top-0 left-0 w-full h-full z-0" />
        </div>
    );
}

export default Learnmore;
