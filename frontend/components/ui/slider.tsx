"use client"

import * as React from "react"
import * as SliderPrimitive from "@radix-ui/react-slider"
import { cn } from "@/lib/utils"

const emojis = ["😢","😒","🫠", "😁", "😀"]

export default function EmojiSlider({ className, ...props }: { className?: string }) {
  const [value, setValue] = React.useState([50]) // middle by default

  
  const getEmoji = (val: number) => {
    if (val < 20) return emojis[0]
    if (val < 40) return emojis[1]
    if (val < 60) return emojis[2]
    if (val < 80) return emojis[3]
    return emojis[4]
  }

  return (
    <div className="flex flex-col items-center">
      {/* Current Emoji */}
      <div className="text-4xl mb-2">{getEmoji(value[0])}</div>

      {/* Slider */}
      <SliderPrimitive.Root
        value={value}
        onValueChange={setValue}
        max={100}
        step={1}
        className={cn("relative flex w-[200px] h-2 items-center", className)} // shrink width here
        {...props}
      >
        <SliderPrimitive.Track className="relative h-1 w-full grow rounded-full bg-gray-300">
          <SliderPrimitive.Range className="relative h-full rounded-full bg-blue-500" />
        </SliderPrimitive.Track>
        <SliderPrimitive.Thumb className="block h-5 w-5 rounded-full bg-white border shadow" />
      </SliderPrimitive.Root>
    </div>
  )
}
