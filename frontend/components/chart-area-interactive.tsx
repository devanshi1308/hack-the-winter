"use client"

import * as React from "react"
import { Area, AreaChart, CartesianGrid, XAxis } from "recharts"

import { useIsMobile } from "@/hooks/use-mobile"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  ToggleGroup,
  ToggleGroupItem,
} from "@/components/ui/toggle-group"

export const description = "An interactive area chart"

// Dummy data with card titles
const chartData = [
  { date: "2024-06-01", predict: 120, annotate: 200, review: 150, train: 80, analyze: 60 },
  { date: "2024-06-02", predict: 140, annotate: 180, review: 170, train: 90, analyze: 70 },
  { date: "2024-06-03", predict: 160, annotate: 210, review: 130, train: 100, analyze: 80 },
  { date: "2024-06-04", predict: 180, annotate: 190, review: 120, train: 110, analyze: 90 },
  { date: "2024-06-05", predict: 200, annotate: 220, review: 140, train: 120, analyze: 100 },
  { date: "2024-06-06", predict: 170, annotate: 210, review: 160, train: 130, analyze: 110 },
  { date: "2024-06-07", predict: 150, annotate: 230, review: 180, train: 140, analyze: 120 },
  { date: "2024-06-08", predict: 130, annotate: 200, review: 170, train: 150, analyze: 130 },
  { date: "2024-06-09", predict: 110, annotate: 180, review: 160, train: 160, analyze: 140 },
  { date: "2024-06-10", predict: 100, annotate: 170, review: 150, train: 170, analyze: 150 },
]

// Chart config with card titles
const chartConfig = {
  predict: { label: "Self Awareness", color: "#6366f1" },
  annotate: { label: "Self Regulation", color: "#f59e42" },
  review: { label: "Motivation", color: "#10b981" },
  train: { label: "Empathy", color: "#ef4444" },
  analyze: { label: "Social Skills", color: "#f472b6" },
} satisfies ChartConfig

export function ChartAreaInteractive() {
  const isMobile = useIsMobile()
  const [timeRange, setTimeRange] = React.useState("90d")

  React.useEffect(() => {
    if (isMobile) {
      setTimeRange("7d")
    }
  }, [isMobile])

  // Adjust filtering for new dummy data (last 7 days)
  const filteredData = chartData

  return (
    <Card className="@container/card">
      <CardHeader>
        <CardTitle>Your Growth</CardTitle>
        <CardDescription>
          <span className="hidden @[540px]/card:block">
            Total for the last 3 months
          </span>
          <span className="@[540px]/card:hidden">Last 3 months</span>
        </CardDescription>
        <CardAction>
          <ToggleGroup
            type="single"
            value={timeRange}
            onValueChange={setTimeRange}
            variant="outline"
            className="hidden *:data-[slot=toggle-group-item]:!px-4 @[767px]/card:flex"
          >
            <ToggleGroupItem value="90d">Last 3 months</ToggleGroupItem>
            <ToggleGroupItem value="30d">Last 30 days</ToggleGroupItem>
            <ToggleGroupItem value="7d">Last 7 days</ToggleGroupItem>
          </ToggleGroup>
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger
              className="flex w-40 **:data-[slot=select-value]:block **:data-[slot=select-value]:truncate @[767px]/card:hidden"
              size="sm"
              aria-label="Select a value"
            >
              <SelectValue placeholder="Last 3 months" />
            </SelectTrigger>
            <SelectContent className="rounded-xl">
              <SelectItem value="90d" className="rounded-lg">
                Last 3 months
              </SelectItem>
              <SelectItem value="30d" className="rounded-lg">
                Last 30 days
              </SelectItem>
              <SelectItem value="7d" className="rounded-lg">
                Last 7 days
              </SelectItem>
            </SelectContent>
          </Select>
        </CardAction>
      </CardHeader>
      <CardContent className="px-2 pt-4 sm:px-6 sm:pt-6">
        <ChartContainer
          config={chartConfig}
          className="aspect-auto h-[250px] w-full"
        >
          <AreaChart data={filteredData}>
            <defs>
              <linearGradient id="fillPredict" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.8} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0.1} />
              </linearGradient>
              <linearGradient id="fillAnnotate" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f59e42" stopOpacity={0.8} />
                <stop offset="95%" stopColor="#f59e42" stopOpacity={0.1} />
              </linearGradient>
              <linearGradient id="fillReview" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.8} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0.1} />
              </linearGradient>
              <linearGradient id="fillTrain" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.8} />
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0.1} />
              </linearGradient>
              <linearGradient id="fillAnalyze" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f472b6" stopOpacity={0.8} />
                <stop offset="95%" stopColor="#f472b6" stopOpacity={0.1} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="date"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              minTickGap={32}
              tickFormatter={(value) => {
                const date = new Date(value)
                return date.toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                })
              }}
            />
            <ChartTooltip
              cursor={false}
              content={
                <ChartTooltipContent
                  labelFormatter={(value) => {
                    return new Date(value).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                    })
                  }}
                  indicator="dot"
                />
              }
            />
            <Area
              dataKey="predict"
              type="natural"
              fill="url(#fillPredict)"
              stroke="#6366f1"
              stackId="a"
            />
            <Area
              dataKey="annotate"
              type="natural"
              fill="url(#fillAnnotate)"
              stroke="#f59e42"
              stackId="a"
            />
            <Area
              dataKey="review"
              type="natural"
              fill="url(#fillReview)"
              stroke="#10b981"
              stackId="a"
            />
            <Area
              dataKey="train"
              type="natural"
              fill="url(#fillTrain)"
              stroke="#ef4444"
              stackId="a"
            />
            <Area
              dataKey="analyze"
              type="natural"
              fill="url(#fillAnalyze)"
              stroke="#f472b6"
              stackId="a"
            />
          </AreaChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
