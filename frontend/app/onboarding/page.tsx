'use client'
import React from 'react'
import { useState } from 'react'
import { TextGenerateEffect } from "@/components/ui/text-generate-effect";
import { Button } from '@/components/ui/button';
import { ArrowRight } from 'lucide-react';
import { ArrowLeft } from 'lucide-react';

import Slider from '../../components/ui/slider';



function Onboarding() {

    const sentences = [
        { id: 0, text: "How often do you take time to reflect on your emotions and understand why you feel a certain way?" },
        { id: 1, text: "How often do you recognize and understand the feelings of others in different situations?" },
        { id: 2, text: "How often are you able to stay calm and manage your emotions during stressful or challenging situations?" },
        { id: 3, text: "How often do you communicate your feelings clearly and respectfully to others?" },
        { id: 4, text: "How often do you stay motivated and positive, even when faced with setbacks?" },
        { id: 5, text: "How often do you bounce back quickly after experiencing disappointment or failure?" },
        { id: 6, text: "Finally, What area do you want to focus on first?" }
    ];
    const [currentId, setCurrentId] = useState<number>(0);
    const [selections, setSelections] = useState<number[]>(Array(sentences.length).fill(-1));

    // build 5 option objects based on the currentId, wrapping around the sentences array
    // simple editable texts you can modify directly
    // optionsBySentence[i] is an array of 5 option objects for sentence i.
    const optionsBySentence: { id: number; text: string; score: number }[][] = [
        // options for sentence 0
        [
            { id: 0, text: "Rarely", score: 0 },
            { id: 1, text: "Sometimes", score: 0.2 },
            { id: 2, text: "Often", score: 0.4 },
            { id: 3, text: "Very Often", score: 0.6 },
            { id: 4, text: "Always", score: 0.8 }
        ],
        // options for sentence 1
        [
            { id: 0, text: "Rarely", score: 0 },
            { id: 1, text: "Sometimes ", score: 0.2 },
            { id: 2, text: "Often", score: 0.4 },
            { id: 3, text: "Very Often", score: 0.6 },
            { id: 4, text: "Always", score: 0.8 },

        ],
        // options for sentence 2
        [
            { id: 0, text: "Rarely", score: 0 },
            { id: 1, text: "Sometimes", score: 0.2 },
            { id: 2, text: "Often", score: 0.4 },
            { id: 3, text: "Very Often", score: 0.6 },
            { id: 4, text: "Always", score: 0.8 }
        ],
        // options for sentence 3
        [
            { id: 0, text: "Rarely", score: 0 },
            { id: 1, text: "Sometimes", score: 0.2 },
            { id: 2, text: "Often", score: 0.4 },
            { id: 3, text: "Very Often", score: 0.6 },
            { id: 4, text: "Always", score: 0.8 }
        ],
        // options for sentence 4
        [
            { id: 0, text: "Rarely", score: 0 },
            { id: 1, text: "Sometimes", score: 0.2 },
            { id: 2, text: "Often", score: 0.4 },
            { id: 3, text: "Very Often", score: 0.6 },
            { id: 4, text: "Always", score: 0.8 },
        ],
        // options for sentence 5
        [
            { id: 0, text: "Rarely", score: 0 },
            { id: 1, text: "Sometimes", score: 0.2 },
            { id: 2, text: "Often", score: 0.4 },
            { id: 3, text: "Very Often", score: 0.6 },
            { id: 4, text: "Always", score: 0.8 },

        ],
        // options for sentence 6
        [
            { id: 0, text: "Self Awareness", score: 0 },
            { id: 1, text: "Self Regulation", score: 0.2 },
            { id: 2, text: "Motivation", score: 0.4 },
            { id: 3, text: "Empathy", score: 0.6 },
            { id: 4, text: "Social Skills", score: 0.8 },
        ]
    ];

    // pick the 5 options for the current sentence id (wrap if needed)
    const isLastQuestion = currentId === sentences.length - 1;
    const options = optionsBySentence[currentId] || [];

    const handleNext = () => {
        if (!isLastQuestion) {
            setCurrentId(prev => prev + 1);
        } else {

            const score = selections.reduce((acc, sel, idx) => {
                if (sel === -1) return acc;
                return acc + (optionsBySentence[idx][sel]?.score || 0);
            }, 0);

            localStorage.setItem('onboardingScore', score.toString());

            setTimeout(() => {
                window.location.href = '/dashboard'
            }, 2000);
        }
    };


    const handleBack = () => {
        if (currentId > 0) {
            setCurrentId(prev => prev - 1);
        }
    };

    return (
        <>
            <div className="flex items-center justify-center min-h-screen">
                <div className="w-full max-w-2xl mt-[-50] rounded-lg text-center">
                    <TextGenerateEffect
                        key={currentId} // force remount on id change
                        words={sentences.find(s => s.id === currentId)?.text ?? ''}
                    />
                    <div role="radiogroup" aria-label="Generated options" className="flex justify-center mt-20 space-x-4">
                        {options.map((opt, i) => {
                            const btnIndex = i + 1;
                            return (
                                <Button
                                    key={`${currentId}-${opt.id}`}
                                    role="radio"
                                    aria-checked={selections[currentId] === btnIndex}
                                    variant={selections[currentId] === btnIndex ? "default" : "ghost"}
                                    onClick={() => {
                                        const newSelections = [...selections];
                                        newSelections[currentId] = btnIndex;
                                        setSelections(newSelections);
                                    }}>
                                    {opt.text}
                                </Button>
                            );
                        })}
                    </div>
                    <div className="flex justify-center pt-17 space-x-4">

                        <Button variant="ghost" disabled={currentId === 0} onClick={handleBack}>
                            <ArrowLeft /> Back
                        </Button>
                        <Button onClick={handleNext} disabled={selections[currentId] === -1}>
                            {isLastQuestion ? "Finish" : "Next"} <ArrowRight />
                        </Button>

                    </div>
                </div>
            </div>
            <div className="w-full mt-[-175]">
            </div>
            <Slider />
        </>
    )
}

export default Onboarding;
