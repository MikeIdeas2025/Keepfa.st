import Header from "./components/Header";
import Hero from "./components/Hero";
import ProblemSection from "./components/ProblemSection";
import HowItWorks from "./components/HowItWorks";
import SkillsShowcase from "./components/SkillsShowcase";
import ForWho from "./components/ForWho";
import CalEmbed from "./components/CalEmbed";
import Footer from "./components/Footer";

export default function Home() {
  return (
    <>
      <Header />
      <main>
        <Hero />
        <ProblemSection />
        <HowItWorks />
        <SkillsShowcase />
        <ForWho />
        <CalEmbed />
      </main>
      <Footer />
    </>
  );
}
