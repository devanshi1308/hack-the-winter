'use client'

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { 
  IconBrain, 
  IconClock,
  IconCircle,
  IconMusic,
  IconDeviceMobile,
  IconPlayerPause,
  IconPlayerPlay,
  IconPlayerStop,
  IconRefresh,
  IconCircleCheck,
  IconMoodHappy,
  IconBulb,
  IconChartBar,
  IconBook
} from "@tabler/icons-react"
import Link from "next/link"

interface Exercise {
  id: string
  title: string
  category: string
  duration: number
  description: string
  steps: string[]
}

const exercises: Exercise[] = [
  {
    id: 'box-breathing',
    title: 'Box Breathing',
    category: 'Self-Regulation',
    duration: 120, // 2 minutes in seconds
    description: 'A calming breathing technique to help manage stress and anxiety',
    steps: [
      'Inhale for 4 counts',
      'Hold for 4 counts', 
      'Exhale for 4 counts',
      'Hold for 4 counts',
      'Repeat the cycle'
    ]
  },
  {
    id: 'perspective-taking',
    title: 'Perspective Taking',
    category: 'Empathy',
    duration: 180, // 3 minutes
    description: 'Practice understanding situations from different viewpoints',
    steps: [
      'Think of a recent conflict',
      'Describe your perspective',
      'Imagine the other person\'s view',
      'Find common ground',
      'Reflect on learnings'
    ]
  },
  {
    id: 'gratitude-practice',
    title: 'Gratitude Practice',
    category: 'Self-Awareness',
    duration: 300, // 5 minutes
    description: 'Cultivate appreciation and positive emotions',
    steps: [
      'Take three deep breaths',
      'Think of something you\'re grateful for',
      'Feel the emotion deeply',
      'Express gratitude mentally',
      'Repeat with 2 more items'
    ]
  }
]

export default function ExercisePage() {
  const [selectedExercise, setSelectedExercise] = useState<Exercise | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [timeRemaining, setTimeRemaining] = useState(0)
  const [isComplete, setIsComplete] = useState(false)
  const [reflection, setReflection] = useState("")
  const [beforeRating, setBeforeRating] = useState<number | null>(null)
  const [afterRating, setAfterRating] = useState<number | null>(null)

  useEffect(() => {
    let interval: NodeJS.Timeout
    if (isPlaying && timeRemaining > 0) {
      interval = setInterval(() => {
        setTimeRemaining(time => {
          if (time <= 1) {
            setIsPlaying(false)
            setIsComplete(true)
            return 0
          }
          return time - 1
        })
      }, 1000)
    }
    return () => clearInterval(interval)
  }, [isPlaying, timeRemaining])

  const startExercise = (exercise: Exercise) => {
    setSelectedExercise(exercise)
    setTimeRemaining(exercise.duration)
    setCurrentStep(0)
    setIsComplete(false)
    setReflection("")
    setAfterRating(null)
  }

  const togglePlayPause = () => {
    setIsPlaying(!isPlaying)
  }

  const stopExercise = () => {
    setIsPlaying(false)
    setSelectedExercise(null)
    setTimeRemaining(0)
    setCurrentStep(0)
    setIsComplete(false)
  }

  const resetExercise = () => {
    if (selectedExercise) {
      setTimeRemaining(selectedExercise.duration)
      setCurrentStep(0)
      setIsPlaying(false)
      setIsComplete(false)
    }
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const getProgressPercentage = () => {
    if (!selectedExercise) return 0
    return ((selectedExercise.duration - timeRemaining) / selectedExercise.duration) * 100
  }

  const logProgress = () => {
    if (selectedExercise && afterRating !== null) {
      const exerciseLog = {
        date: new Date().toISOString(),
        exerciseId: selectedExercise.id,
        exerciseTitle: selectedExercise.title,
        category: selectedExercise.category,
        completed: true,
        beforeRating,
        afterRating,
        reflection
      }
      
      const existingLogs = JSON.parse(localStorage.getItem('exerciseLogs') || '[]')
      existingLogs.push(exerciseLog)
      localStorage.setItem('exerciseLogs', JSON.stringify(existingLogs))
      
      alert('Progress logged! Redirecting to dashboard...')
      setTimeout(() => {
        window.location.href = '/dashboard'
      }, 1000)
    }
  }

  if (selectedExercise && !isComplete) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-2xl">
        <Card>
          <CardHeader className="text-center">
            <CardTitle className="text-2xl">{selectedExercise.title}</CardTitle>
            <CardDescription className="flex items-center gap-2">
              <IconClock className="h-4 w-4" />
              {Math.floor(selectedExercise.duration / 60)} minutes • {selectedExercise.category}
            </CardDescription>
          </CardHeader>
          
          <CardContent className="space-y-6">
            {/* Exercise Visual */}
            <div className="flex flex-col items-center space-y-4">
              <div className="w-32 h-32 rounded-full border-4 border-blue-500 flex items-center justify-center text-4xl">
                <IconCircle className="h-16 w-16 text-blue-500" />
              </div>
              
              <div className="text-center">
                <div className="text-2xl font-bold">
                  {selectedExercise.steps[Math.min(currentStep, selectedExercise.steps.length - 1)]}
                </div>
                <div className="text-lg text-muted-foreground mt-2 flex items-center gap-2">
                  <IconClock className="h-4 w-4" />
                  {formatTime(timeRemaining)} / {formatTime(selectedExercise.duration)}
                </div>
              </div>
              
              <div className="w-full max-w-md">
                <div className="w-full bg-muted rounded-full h-2">
                  <div 
                    className="bg-blue-500 h-2 rounded-full transition-all duration-1000" 
                    style={{ width: `${getProgressPercentage()}%` }}
                  />
                </div>
              </div>
              
              <div className="text-sm text-muted-foreground">
                Step {currentStep + 1} of {selectedExercise.steps.length}
              </div>
            </div>

            {/* Exercise Settings */}
            <Card className="bg-muted/30">
              <CardContent className="p-4">
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <IconMusic className="h-4 w-4" />
                    <span>Background: Nature sounds</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <IconDeviceMobile className="h-4 w-4" />
                    <span>Haptic: Gentle vibration</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Controls */}
            <div className="flex justify-center space-x-4">
              <Button
                onClick={togglePlayPause}
                size="lg"
                className="flex items-center gap-2"
              >
                {isPlaying ? <IconPlayerPause className="h-4 w-4" /> : <IconPlayerPlay className="h-4 w-4" />}
                {isPlaying ? 'Pause' : 'Play'}
              </Button>
              <Button
                onClick={stopExercise}
                variant="outline"
                size="lg"
                className="flex items-center gap-2"
              >
                <IconPlayerStop className="h-4 w-4" />
                Stop
              </Button>
              <Button
                onClick={resetExercise}
                variant="outline"
                size="lg"
                className="flex items-center gap-2"
              >
                <IconRefresh className="h-4 w-4" />
                Reset
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (isComplete && selectedExercise) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-2xl">
        <Card>
          <CardHeader className="text-center">
            <CardTitle className="text-2xl flex items-center justify-center gap-2">
              <IconCircleCheck className="h-6 w-6 text-green-500" />
              Exercise Complete!
            </CardTitle>
            <CardDescription>
              Great job completing {selectedExercise.title}
            </CardDescription>
          </CardHeader>
          
          <CardContent className="space-y-6">
            <div className="text-center text-lg flex items-center justify-center gap-2">
              <IconMoodHappy className="h-6 w-6 text-yellow-500" />
              Well done! How do you feel now?
            </div>
            
            {/* Before/After Rating */}
            <div className="space-y-4">
              {beforeRating === null && (
                <div>
                  <p className="mb-3 font-medium">How did you feel before the exercise?</p>
                  <div className="flex justify-center space-x-2">
                    {[1, 2, 3, 4, 5].map((rating) => (
                      <Button
                        key={rating}
                        onClick={() => setBeforeRating(rating)}
                        variant="outline"
                        size="sm"
                      >
                        {rating}
                      </Button>
                    ))}
                  </div>
                  <div className="text-center text-sm text-muted-foreground mt-2">
                    Much worse ← → Much better
                  </div>
                </div>
              )}
              
              {beforeRating !== null && afterRating === null && (
                <div>
                  <p className="mb-3 font-medium">How do you feel now?</p>
                  <div className="flex justify-center space-x-2">
                    {[1, 2, 3, 4, 5].map((rating) => (
                      <Button
                        key={rating}
                        onClick={() => setAfterRating(rating)}
                        variant="outline"
                        size="sm"
                      >
                        {rating}
                      </Button>
                    ))}
                  </div>
                  <div className="text-center text-sm text-muted-foreground mt-2">
                    Much worse ← → Much better
                  </div>
                </div>
              )}
            </div>

            {/* Reflection */}
            {afterRating !== null && (
              <div className="space-y-3">
                <p className="font-medium flex items-center gap-2">
                  <IconBulb className="h-4 w-4" />
                  Quick reflection:
                </p>
                <p className="text-sm text-muted-foreground">
                  What changed in your body during this exercise?
                </p>
                <Textarea
                  placeholder="I noticed my breathing became slower and my shoulders relaxed..."
                  value={reflection}
                  onChange={(e) => setReflection(e.target.value)}
                  className="min-h-[80px]"
                />
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-3">
              <Button 
                onClick={logProgress}
                disabled={afterRating === null}
                className="flex-1 flex items-center gap-2"
              >
                <IconChartBar className="h-4 w-4" />
                Log Progress
              </Button>
              <Button 
                onClick={resetExercise}
                variant="outline"
                className="flex-1 flex items-center gap-2"
              >
                <IconRefresh className="h-4 w-4" />
                Repeat
              </Button>
            </div>
            
            <div className="text-center">
              <Link href="/community-wellness">
                <Button variant="ghost" className="flex items-center gap-2">
                  <IconBook className="h-4 w-4" />
                  Related Exercises
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Exercise selection screen
  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold mb-2 flex items-center justify-center gap-2">
          <IconBrain className="h-8 w-8 text-blue-500" />
          Guided Exercises
        </h1>
        <p className="text-muted-foreground">
          Choose an exercise to practice emotional intelligence skills
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {exercises.map((exercise) => (
          <Card key={exercise.id} className="hover:shadow-lg transition-shadow cursor-pointer">
            <CardHeader>
              <div className="flex items-start justify-between">
                <CardTitle className="text-lg">{exercise.title}</CardTitle>
                <Badge variant="secondary">{exercise.category}</Badge>
              </div>
              <CardDescription className="flex items-center gap-2">
                <IconClock className="h-4 w-4" />
                {Math.floor(exercise.duration / 60)} min • {exercise.description}
              </CardDescription>
            </CardHeader>
            
            <CardContent className="space-y-4">
              <div>
                <h4 className="font-medium mb-2">Exercise Steps:</h4>
                <ul className="text-sm space-y-1">
                  {exercise.steps.slice(0, 3).map((step, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <span className="text-blue-500">•</span>
                      {step}
                    </li>
                  ))}
                  {exercise.steps.length > 3 && (
                    <li className="text-muted-foreground">+ {exercise.steps.length - 3} more steps</li>
                  )}
                </ul>
              </div>
              
              {['box-breathing', 'perspective-taking', 'gratitude-practice'].includes(exercise.id) ? (
                <Link href={`/exercise/${exercise.id}`}>
                  <Button className="w-full flex items-center gap-2">
                    <IconPlayerPlay className="h-4 w-4" />
                    Start Exercise
                  </Button>
                </Link>
              ) : (
                <Button 
                  onClick={() => startExercise(exercise)}
                  className="w-full flex items-center gap-2"
                >
                  <IconPlayerPlay className="h-4 w-4" />
                  Start Exercise
                </Button>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}