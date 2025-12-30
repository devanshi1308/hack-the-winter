"use client";

import React, { useEffect, useState } from "react";
import { TextGenerateEffect } from "@/components/ui/text-generate-effect";
import { Button } from "@/components/ui/button";
import { ArrowRight, ArrowLeft } from "lucide-react";
import { useRouter } from "next/navigation";
import { apiClient, handleApiError } from "@/lib/api";

interface Question {
  id: string;
  text: string;
  scale: string;
  facet?: string;
  reverse_score?: boolean;
}

function getFallbackQuestions(): Question[] {
  return [
    { id: "mood",        text: "How are you feeling today?",                         scale: "1 = Very Low, 5 = Very High" },
    { id: "stress",      text: "How stressed did you feel today?",                   scale: "1 = Not at all, 5 = Extremely" },
    { id: "energy",      text: "What's your energy level right now?",                scale: "1 = Very Low, 5 = Very High" },
    { id: "connection",  text: "How connected did you feel to others today?",        scale: "1 = Not at all, 5 = Very Connected" },
    { id: "motivation",  text: "How motivated did you feel today?",                  scale: "1 = Not at all, 5 = Extremely" },
  ];
}

export default function Today() {
  const router = useRouter();

  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentId, setCurrentId] = useState<number>(0);
  const [responses, setResponses] = useState<Record<string, number>>({});
  const [isComplete, setIsComplete] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isOffline, setIsOffline] = useState(false);
  const [hasCheckedInToday, setHasCheckedInToday] = useState(false);

  // Load questions + early exit if already checked-in today
  useEffect(() => {
    (async () => {
      try {
        const lastCheckIn = typeof window !== "undefined" ? localStorage.getItem("lastCheckIn") : null;
        const today = new Date().toDateString();
        // If user already checked in today, don't auto-redirect.
        // Show a banner with options instead.
        if (lastCheckIn === today) {
          setHasCheckedInToday(true);
        }

        const data = await apiClient.getCheckInQuestions();
        if (data?.questions?.length) {
          setQuestions(data.questions);
          setIsOffline(false);
        } else {
          setQuestions(getFallbackQuestions());
          setIsOffline(true);
        }
      } catch (err) {
        console.warn("Using offline questions");
        handleApiError(err, "getCheckInQuestions");
        setQuestions(getFallbackQuestions());
        setIsOffline(true);
      } finally {
        setIsLoading(false);
      }
    })();
  }, [router]);

  const handleRedoCheckIn = () => {
    // Allow user to redo today's check-in from this page
    localStorage.removeItem("lastCheckIn");
    localStorage.removeItem("lastResponses");
    localStorage.removeItem("dailyScore");
    setHasCheckedInToday(false);
    setIsComplete(false);
    setResponses({});
    setCurrentId(0);
  };

  const handleCompletion = async () => {
    if (isSubmitting) return;
    setIsSubmitting(true);

    try {
      setIsComplete(true);

      const userId = localStorage.getItem("user_id") || `temp-user-${Date.now()}`;
      const checkInData = {
        user_id: userId,
        date: new Date().toISOString().split("T")[0],
        ...responses,
      };

      const result = await apiClient.submitCheckIn(checkInData);

      // Persist locally for dashboard
      localStorage.setItem("lastCheckIn", new Date().toDateString());
      localStorage.setItem("lastResponses", JSON.stringify(responses));
      localStorage.setItem("dailyScore", result?.mood_index?.toString() || "0");
      localStorage.setItem("user_id", userId);
    } catch (err) {
      handleApiError(err, "submitCheckIn");
      // still proceed to dashboard on failure
    } finally {
      setIsSubmitting(false);
      setTimeout(() => router.push("/dashboard"), 800);
    }
  };

  const handleNext = () => {
    if (currentId < questions.length - 1) {
      setCurrentId((p) => p + 1);
    } else {
      void handleCompletion();
    }
  };

  const handleBack = () => {
    if (currentId > 0) setCurrentId((p) => p - 1);
  };

  const handleResponse = (value: number) => {
    const q = questions[currentId];
    if (!q) return;
    setResponses((prev) => ({ ...prev, [q.id]: value }));
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl">Loading questions…</div>
      </div>
    );
  }

  const currentQuestion = questions[currentId];
  const isLastQuestion = currentId === questions.length - 1;
  const hasResponse =
    currentQuestion && responses[currentQuestion.id] !== undefined;

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="w-full max-w-2xl mt-[-50] rounded-lg text-center">
        {isOffline && (
          <div className="mb-4 p-3 bg-yellow-100 dark:bg-yellow-900 border border-yellow-400 text-yellow-700 dark:text-yellow-300 rounded">
            ⚠️ Offline mode — your data will be saved locally.
          </div>
        )}

        {hasCheckedInToday && !isComplete && (
          <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/40 border border-blue-300 text-blue-800 dark:text-blue-200 rounded flex flex-col sm:flex-row items-center justify-between gap-3">
            <span>You already completed today’s check-in.</span>
            <div className="flex gap-2">
              <Button variant="ghost" onClick={() => router.push('/dashboard')}>View Dashboard</Button>
              <Button onClick={handleRedoCheckIn}>Redo Check-in</Button>
            </div>
          </div>
        )}

        {isComplete ? (
          <div className="text-xl font-medium text-green-600 mb-4">
            {isSubmitting ? (
              <>
                <div className="animate-spin h-6 w-6 border-2 border-green-600 border-t-transparent rounded-full mx-auto mb-2" />
                Saving your responses…
              </>
            ) : (
              "Thank you for completing your daily check-in! Redirecting…"
            )}
          </div>
        ) : (
          <>
            <div className="mb-4 text-sm text-muted-foreground">
              Question {currentId + 1} of {questions.length}
            </div>

            <TextGenerateEffect key={currentId} words={currentQuestion?.text || ""} />

            <div className="mt-8 mb-4 text-sm text-muted-foreground">
              {currentQuestion?.scale}
            </div>

            <div className="flex justify-center mt-20 space-x-2">
              {[1, 2, 3, 4, 5].map((value) => (
                <Button
                  key={value}
                  variant={
                    currentQuestion &&
                    responses[currentQuestion.id] === value
                      ? "default"
                      : "ghost"
                  }
                  onClick={() => handleResponse(value)}
                  className="min-w-12 h-12 text-lg"
                >
                  {value}
                </Button>
              ))}
            </div>

            <div className="flex justify-center pt-17 space-x-4">
              <Button variant="ghost" disabled={currentId === 0} onClick={handleBack}>
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>

              <Button onClick={handleNext} disabled={!hasResponse}>
                {isLastQuestion ? "Finish" : "Next"}
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
