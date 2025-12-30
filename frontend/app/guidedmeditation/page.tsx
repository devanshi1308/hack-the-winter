'use client'
import React from 'react'
import Card from '@/components/ui/card2'

export default function GuidedMeditationPage() {
  return (
    <div className="p-4 min-h-screen flex items-center justify-center">
      <Card
        title="Guided Meditation"
        description="Take a few minutes to calm your mind and nurture emotional wellbeing."
        imageUrl="https://images.unsplash.com/photo-1737639441322-8d083c13eb6a?q=80&w=1171&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
      />
    </div>
  )
}
