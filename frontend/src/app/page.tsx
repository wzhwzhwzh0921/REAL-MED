import { Footer } from "@/components/landing/footer";
import { Header } from "@/components/landing/header";
import { Hero } from "@/components/landing/hero";
import { CommunitySection } from "@/components/landing/sections/community-section";

export default function LandingPage() {
  return (
    <div className="min-h-screen w-full bg-[#0a0a0a]">
      <Header />
      <main className="flex w-full flex-col">
        <Hero />
        <CommunitySection />
      </main>
      <Footer />
    </div>
  );
}
