"use client";
import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TextGenerateEffect } from "@/components/ui/text-generate-effect";
import { PenTool } from "lucide-react";

function CollabRewriter() {
  const [inputText, setInputText] = useState("");
  const [rewrittenText, setRewrittenText] = useState("");
  const [isRewriting, setIsRewriting] = useState(false);
  const [error, setError] = useState("");
  const [showResult, setShowResult] = useState(false);

  const handleRewrite = async () => {
    if (!inputText.trim()) return;
    
    setIsRewriting(true);
    setError("");
    setShowResult(false);
  
    try {
      const response = await fetch('/api/rewrite', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: inputText }),
      });

      const data = await response.json();

      if (!response.ok) {
        if (response.status === 503) {
          throw new Error("The AI service is busy right now. Please try again in a few moments.");
        }
        throw new Error(data.error || 'Failed to rewrite text');
      }

      setRewrittenText(data.rewrittenText);
      setShowResult(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to rewrite text. Please try again.");
      console.error("Rewrite error:", err);
    } finally {
      setIsRewriting(false);
    }
  };

  return (
    <div className="min-h-screen bg-background p-4">
      <div className="flex items-center justify-center min-h-screen">
        <div className="w-full max-w-5xl space-y-8">
          {/* Header */}
          <div className="text-center space-y-4">
            <div className="flex items-center justify-center space-x-3 mb-6">
              <PenTool className="h-8 w-8 text-primary" />
              <h1 className="text-4xl font-bold text-foreground">Collab Rewriter</h1>
            </div>
            <TextGenerateEffect 
              words="Transform your text with AI-powered rewriting. Enter your content below and watch it become more engaging and polished."
            />
          </div>

          {/* Main Content */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Input Section */}
            <Card className="border-border bg-card">
              <CardHeader>
                <CardTitle className="text-xl font-semibold text-card-foreground flex items-center space-x-2">
                  <span>Original Text</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="text-input" className="text-sm font-medium text-muted-foreground">
                    Enter your text here
                  </Label>
                  <textarea
                    id="text-input"
                    className="w-full min-h-[400px] p-4 border border-input bg-background rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent text-foreground placeholder:text-muted-foreground transition-colors"
                    placeholder="Paste or type the text you want to rewrite here..."
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                  />
                </div>
                
                <div className="flex justify-center pt-4">
                  <Button
                    onClick={handleRewrite}
                    disabled={!inputText.trim() || isRewriting}
                    size="lg"
                    className="px-8 py-3 text-lg font-medium bg-primary hover:bg-primary/90 text-primary-foreground transition-colors"
                  >
                    {isRewriting ? (
                      <>
                        <div className="animate-spin h-5 w-5 mr-2 border-2 border-primary-foreground border-t-transparent rounded-full" />
                        Rewriting...
                      </>
                    ) : (
                      <>
                        <PenTool className="h-5 w-5 mr-2" />
                        Rewrite
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Output Section */}
            <Card className="border-border bg-card">
              <CardHeader>
                <CardTitle className="text-xl font-semibold text-card-foreground">
                  Rewritten Text
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {error && (
                  <div className="p-4 border border-destructive/20 bg-destructive/10 rounded-lg text-destructive text-sm">
                    {error}
                  </div>
                )}

                {showResult && rewrittenText && (
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-muted-foreground">
                      AI-Enhanced Version
                    </Label>
                    <div className="p-4 border border-primary/20 bg-primary/5 rounded-lg min-h-[400px]">
                      <TextGenerateEffect 
                        words={rewrittenText}
                        className="text-foreground leading-relaxed"
                      />
                    </div>
                  </div>
                )}

                {!showResult && !error && !isRewriting && (
                  <div className="flex items-center justify-center min-h-[400px] text-muted-foreground">
                    <div className="text-center space-y-2">
                      <PenTool className="h-12 w-12 mx-auto opacity-50" />
                      <p>Your rewritten text will appear here</p>
                    </div>
                  </div>
                )}

                {isRewriting && (
                  <div className="flex items-center justify-center min-h-[400px] text-muted-foreground">
                    <div className="text-center space-y-4">
                      <div className="animate-spin h-8 w-8 mx-auto border-2 border-primary border-t-transparent rounded-full" />
                      <p>AI is rewriting your text...</p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CollabRewriter;
