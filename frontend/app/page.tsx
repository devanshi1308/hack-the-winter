import { TextHoverEffect } from "@/components/ui/text-hover-effect";
import { TextGenerateEffect } from "@/components/ui/text-generate-effect";
import { Button } from "@/components/ui/button";

import Link from "next/link";

export default function Home() {
  const words: string = "decode your emotions, master your life.";

  return (
    <div className="p-5 m-5">
      <title>RaAI</title>
      <main className="min-h-screen flex flex-col items-center justify-center mt-[-120] ">
        <TextHoverEffect text="Ra.AI" />
        <div className="flex justify-center w-full md:mt-[-90] sm:mt-20">
          <TextGenerateEffect words={words} />
        </div>
      </main>
      <div className="w-full flex justify-center mt-[-90]">
        <div className="flex gap-4 mt-[-100] md:mt-0">
          <Link href="/onboarding">
            <Button
              className="bg-accent text-accent-foreground hover:bg-accent/90"
              aria-label="Get started"
            >
              Get started
            </Button>
          </Link>
          <Button variant="ghost" aria-label="Learn more">
            Learn more
          </Button>
        </div>
      </div>
      <div className="w-full mt-4"></div>

    </div>
  );
}
