'use client';

import React, { useState } from 'react';
import { CardContainer, CardBody, CardItem } from "@/components/ui/3d-card";
import { Button } from "@/components/ui/button";
import { twMerge } from 'tailwind-merge';
import { BackgroundBeams } from "@/components/ui/BackgroundBeams";
import { IconFlame } from "@tabler/icons-react";

// Define the shape of our data
interface Challenge {
    id: string;
    title: string;
    description: string;
    reward: string;
}

interface UserChallenge {
    challengeId: string;
    currentStreak: number;
    lastCompletedDate: string;
}

const cn = (...classNames: (string | boolean | undefined | null)[]) => 
    twMerge(...classNames.filter((className): className is string => typeof className === 'string' && className.length > 0));
const mockChallenges: Challenge[] = [
    { id: '1', title: 'Daily Gratitude', description: 'Write down three things you are grateful for each day.', reward: 'A sense of calm' },
    { id: '2', title: 'Mindful Breathing', description: 'Practice 5 minutes of focused breathing.', reward: 'Reduced stress' },
    { id: '3', title: 'Positive Affirmations', description: 'Repeat a positive affirmation to yourself.', reward: 'Increased confidence' },
    { id: '4', title: 'Random Acts of Kindness', description: 'Perform a kind act for someone else.', reward: 'Boosted mood' },
    { id: '5', title: 'Digital Detox', description: 'Spend one hour without any digital devices.', reward: 'Mental clarity' },
    { id: '6', title: 'Nature Walk', description: 'Take a 20-minute walk outside.', reward: 'Improved focus' },
];

const Challenges = () => {
    const [challenges, setChallenges] = useState<Challenge[]>(mockChallenges);
    const [userChallenges, setUserChallenges] = useState<{ [key: string]: UserChallenge }>({});
    const [userId, setUserId] = useState<string | null>('mock-user-1234');
    const [loading, setLoading] = useState<boolean>(false);

    const handleJoinChallenge = (challengeId: string) => {
        setUserChallenges(prev => ({
            ...prev,
            [challengeId]: { challengeId, currentStreak: 0, lastCompletedDate: '' }
        }));
    };

    const handleCompleteDay = async (challengeId: string) => {
        const today = new Date().toISOString().slice(0, 10);
        
        // Update state first
        await new Promise<void>(resolve => {
            setUserChallenges(prev => {
                const currentData = prev[challengeId];
                if (currentData.lastCompletedDate === today) {
                    resolve();
                    return prev;
                }
                resolve();
                return {
                    ...prev,
                    [challengeId]: {
                        ...currentData,
                        currentStreak: currentData.currentStreak + 1,
                        lastCompletedDate: today
                    }
                };
            });
        });

        // Redirect based on challenge ID after state is updated
        if (challengeId === '1') { // Daily Gratitude
            window.location.href = '/exercise/gratitude-practice';
        } else if (challengeId === '2') { // Mindful Breathing
            window.location.href = '/exercise/box-breathing';
        } else if (challengeId === '3') { // Positive Affirmations
            window.location.href = '/exercise/perspective-taking';
        }
    };

    if (loading) {
        return <div className="text-center text-white text-xl">Loading challenges...</div>;
    }

    if (!userId) {
        return <div className="text-center text-white text-xl">Please wait, authenticating...</div>;
    }

    return (
        // Added relative positioning and a higher z-index to the main container
        // to ensure content is above the BackgroundBeams.
        <div className="relative w-full min-h-screen pt-24 pb-12 flex flex-col items-center">
            <div className="relative z-10 w-full max-w-7xl mx-auto px-4">
                <h1 className="text-center text-4xl sm:text-5xl font-bold mb-4 bg-gradient-to-r from-purple-400 to-indigo-600 text-transparent bg-clip-text">
                    Community Challenges
                </h1>
                <p className="text-center text-lg sm:text-xl text-muted-foreground mb-12">
                    Join a challenge and build your emotional wellness streak. Your User ID: {userId}
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                    {challenges.map(challenge => {
                        const userHasJoined = !!userChallenges[challenge.id];
                        const userStreak = userHasJoined ? userChallenges[challenge.id].currentStreak : 0;
                        const canCompleteToday = userHasJoined && userChallenges[challenge.id].lastCompletedDate !== new Date().toISOString().slice(0, 10);

                        return (
                            <CardContainer 
                                key={challenge.id} 
                                // Cleaned up containerClassName for better alignment
                                containerClassName="w-full flex justify-center items-center" 
                                // Added a fixed width to the card for consistent 3D effect.
                                className="w-full h-auto max-w-sm"
                            >
                                <CardBody 
                                    className="bg-card text-card-foreground relative group/card w-full h-auto rounded-xl p-6 border border-gray-700 shadow-lg hover:shadow-2xl transition-all duration-300"
                                >
                                    <CardItem
                                        translateZ="50"
                                        className="text-xl font-bold text-card-foreground mb-2"
                                    >
                                        {challenge.title}
                                    </CardItem>
                                    <CardItem
                                        as="p"
                                        translateZ="60"
                                        className="text-muted-foreground text-sm mt-2 mb-4"
                                    >
                                        {challenge.description}
                                    </CardItem>
                                    <CardItem translateZ="40" className="w-full mt-4">
                                        <div className="text-lg font-semibold">
                                            Reward: <span className="text-purple-400">{challenge.reward}</span>
                                        </div>
                                    </CardItem>
                                    <CardItem translateZ="30" className="w-full mt-2 mb-6">
                                        <div className="flex items-center text-lg">
                                            Your Streak: <span className="ml-2 font-bold text-yellow-400">{userStreak}</span>
                                            <IconFlame className="ml-1 h-5 w-5 text-yellow-400" />
                                        </div>
                                    </CardItem>
                                    <CardItem
                                        translateZ={20}
                                        as="div"
                                        className="w-full mt-auto"
                                    >
                                        {!userHasJoined ? (
                                            <Button
                                                onClick={() => handleJoinChallenge(challenge.id)}
                                                className="w-full"
                                            >
                                                Join Challenge
                                            </Button>
                                        ) : (
                                            <Button
                                                onClick={() => handleCompleteDay(challenge.id)}
                                                disabled={!canCompleteToday}
                                                className={cn(
                                                    "w-full font-bold",
                                                    !canCompleteToday && "cursor-not-allowed"
                                                )}
                                                variant={canCompleteToday ? "default" : "secondary"}
                                            >
                                                {canCompleteToday ? "Complete Today" : "Completed!"}
                                            </Button>
                                        )}
                                    </CardItem>
                                </CardBody>
                            </CardContainer>
                        );
                    })}
                </div>

            </div>
            <BackgroundBeams className="absolute top-0 left-0 w-full h-full -z-10 pointer-events-none" />
        </div>
    );
};
export default Challenges;
