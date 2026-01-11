"use client"
import Link from "next/link"
import { useState } from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Eye, EyeOff } from "lucide-react"

export function SignupForm({ className, ...props }: React.ComponentProps<"div">) {
  const [showPassword, setShowPassword] = useState(false)

  return (
    <div className={cn("flex flex-col gap-6", className)} {...props}>
      <div className="relative">
        {/* Soft radial glow background (same as Login) */}
        <div className="absolute inset-0 -z-10 rounded-lg bg-gradient-radial from-primary/10 via-transparent to-transparent blur-3xl" />

        <Card>
          <CardHeader>
            <CardTitle>Create your account</CardTitle>
            <CardDescription>
              Sign up to start your journey
            </CardDescription>
          </CardHeader>

          {/* Divider same as Login */}
          <div className="mx-6 h-px bg-border/60" />

          <CardContent>
            <form>
              <div className="flex flex-col gap-6">
                {/* Name */}
                <div className="grid gap-3">
                  <Label htmlFor="name">Name</Label>
                  <Input
                    id="name"
                    type="text"
                    placeholder="Your name"
                    required
                    className="focus-visible:ring-2 focus-visible:ring-primary"
                  />
                </div>

                {/* Email */}
                <div className="grid gap-3">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="m@example.com"
                    required
                    className="focus-visible:ring-2 focus-visible:ring-primary"
                  />
                </div>

                {/* Password */}
                <div className="grid gap-3">
                  <Label htmlFor="password">Password</Label>
                  <div className="relative">
                    <Input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      required
                      className="focus-visible:ring-2 focus-visible:ring-primary"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                {/* Submit button */}
                <div className="flex flex-col gap-3">
                  <Button
                    type="submit"
                    className="w-full focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
                  >
                    Sign up
                  </Button>
                </div>
              </div>

              {/* Footer link */}
              <div className="mt-4 text-center text-sm">
                Already have an account?{" "}
                <Link
                  href="/login"
                  className="underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2 rounded"
                >
                  Login
                </Link>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Bottom tagline */}
        <p className="text-center text-base text-muted-foreground/50 mt-4">
          Your space. Your pace. Your emotions.
        </p>
      </div>
    </div>
  )
}

export default SignupForm
