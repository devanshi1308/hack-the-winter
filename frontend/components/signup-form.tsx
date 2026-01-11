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

const TAGLINE = "Your space. Your pace. Your emotions."

export function SignupForm({
  className,
  ...props
}: React.ComponentProps<"div">) {
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [errors, setErrors] = useState<{
    name?: string
    email?: string
    password?: string
    confirmPassword?: string
  }>({})

  const validateForm = () => {
    const newErrors: {
      name?: string
      email?: string
      password?: string
      confirmPassword?: string
    } = {}

    if (!name.trim()) {
      newErrors.name = "Name is required"
    }

    if (!email) {
      newErrors.email = "Email is required"
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      newErrors.email = "Please enter a valid email"
    }

    if (!password) {
      newErrors.password = "Password is required"
    } else if (password.length < 8) {
      newErrors.password = "Password must be at least 8 characters"
    }

    if (!confirmPassword) {
      newErrors.confirmPassword = "Please confirm your password"
    } else if (password !== confirmPassword) {
      newErrors.confirmPassword = "Passwords do not match"
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm()) {
      return
    }

    setIsLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
      const response = await fetch(`${apiUrl}/api/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        setErrors({ email: errorData.detail || "Signup failed" })
      } else {
        const data = await response.json()
        
        // Store auth token
        if (typeof window !== "undefined") {
          localStorage.setItem("auth_token", data.token)
          localStorage.setItem("user_id", data.user_id)
          localStorage.setItem("user_email", data.email)
          localStorage.setItem("user_name", data.name)
        }
        
        // Handle successful signup - redirect to dashboard or onboarding
        window.location.href = "/onboarding"
      }
    } catch (_error) {
      setErrors({ email: "An error occurred. Please try again." })
    } finally {
      setIsLoading(false)
    }
  }

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
            <form onSubmit={handleSubmit}>
              <div className="flex flex-col gap-6">
                {/* Name */}
                <div className="grid gap-3">
                  <Label htmlFor="name">Name</Label>
                  <Input
                    id="name"
                    type="text"
                    placeholder="Your name"
                    value={name}
                    onChange={(e) => {
                      setName(e.target.value)
                      if (errors.name) setErrors({ ...errors, name: undefined })
                    }}
                    required
                    className={cn(
                      "focus-visible:ring-2 focus-visible:ring-primary",
                      errors.name && "border-red-500"
                    )}
                  />
                  {errors.name && (
                    <p className="text-sm text-red-500">{errors.name}</p>
                  )}
                </div>

                {/* Email */}
                <div className="grid gap-3">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="m@example.com"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value)
                      if (errors.email) setErrors({ ...errors, email: undefined })
                    }}
                    required
                    className={cn(
                      "focus-visible:ring-2 focus-visible:ring-primary",
                      errors.email && "border-red-500"
                    )}
                  />
                  {errors.email && (
                    <p className="text-sm text-red-500">{errors.email}</p>
                  )}
                </div>

                {/* Password */}
                <div className="grid gap-3">
                  <Label htmlFor="password">Password</Label>
                  <div className="relative">
                    <Input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => {
                        setPassword(e.target.value)
                        if (errors.password)
                          setErrors({ ...errors, password: undefined })
                      }}
                      required
                      className={cn(
                        "focus-visible:ring-2 focus-visible:ring-primary",
                        errors.password && "border-red-500"
                      )}
                    />
                    <button
                      type="button"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors focus-visible:outline-2 focus-visible:outline-primary rounded p-1"
                    >
                      {showPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                  {errors.password && (
                    <p className="text-sm text-red-500">{errors.password}</p>
                  )}
                </div>

                {/* Confirm Password */}
                <div className="grid gap-3">
                  <Label htmlFor="confirm-password">Confirm Password</Label>
                  <div className="relative">
                    <Input
                      id="confirm-password"
                      type={showConfirmPassword ? "text" : "password"}
                      value={confirmPassword}
                      onChange={(e) => {
                        setConfirmPassword(e.target.value)
                        if (errors.confirmPassword)
                          setErrors({
                            ...errors,
                            confirmPassword: undefined,
                          })
                      }}
                      required
                      className={cn(
                        "focus-visible:ring-2 focus-visible:ring-primary",
                        errors.confirmPassword && "border-red-500"
                      )}
                    />
                    <button
                      type="button"
                      aria-label={
                        showConfirmPassword
                          ? "Hide password"
                          : "Show password"
                      }
                      onClick={() =>
                        setShowConfirmPassword(!showConfirmPassword)
                      }
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors focus-visible:outline-2 focus-visible:outline-primary rounded p-1"
                    >
                      {showConfirmPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                  {errors.confirmPassword && (
                    <p className="text-sm text-red-500">
                      {errors.confirmPassword}
                    </p>
                  )}
                </div>

                {/* Submit button */}
                <div className="flex flex-col gap-3">
                  <Button
                    type="submit"
                    disabled={isLoading}
                    className="w-full focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
                  >
                    {isLoading ? "Creating account..." : "Sign up"}
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
          {TAGLINE}
        </p>
      </div>
    </div>
  )
}
