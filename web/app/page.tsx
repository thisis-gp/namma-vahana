import Link from "next/link";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import CityMap from "@/components/landing/CityMap";
import ActivityTicker from "@/components/hero/ActivityTicker";
import LandingStats from "@/components/landing/LandingStats";
import { BRAND } from "@/lib/brand";

export default function Landing() {
  return (
    <>
      <Nav />
      <main>
        {/* Hero */}
        <section
          id="top"
          className="relative overflow-hidden border-b border-line"
          style={{
            background:
              "radial-gradient(120% 90% at 90% -10%, var(--cobalt-soft) 0%, var(--ground) 50%)",
          }}
        >
          <div className="mx-auto grid w-full max-w-6xl items-center gap-10 px-5 pb-16 pt-16 sm:px-8 sm:pb-20 sm:pt-24 lg:grid-cols-[1.05fr_0.95fr]">
            <div>
              <p className="eyebrow reveal mb-5">
                {BRAND.tagline} · built on real enforcement data
              </p>
              <h1
                className="font-display reveal text-4xl font-extrabold leading-[1.04] tracking-tight sm:text-6xl"
                style={{ animationDelay: "0.08s" }}
              >
                Park without the{" "}
                <span className="text-cobalt">guesswork.</span> Enforce without
                the <span className="text-cobalt">guessing.</span>
              </h1>
              <p
                className="reveal mt-5 max-w-xl text-lg leading-relaxed text-ink-muted"
                style={{ animationDelay: "0.16s" }}
              >
                One dataset of 2,98,443 parking violations, two jobs done well:
                residents find low-risk parking and avoid fines; the traffic
                police see where to be, when, and with whom.
              </p>

              {/* Two doors */}
              <div
                className="reveal mt-8 flex flex-col gap-3 sm:flex-row"
                style={{ animationDelay: "0.24s" }}
              >
                <Link
                  href="/resident"
                  className="group flex flex-1 items-center justify-between rounded-xl bg-cobalt px-5 py-4 text-white transition-colors hover:bg-cobalt-deep"
                >
                  <span>
                    <span className="block text-base font-semibold">
                      I’m a resident
                    </span>
                    <span className="text-sm text-white/80">
                      Find parking · avoid fines · earn green points
                    </span>
                  </span>
                  <span className="text-xl transition-transform group-hover:translate-x-0.5">
                    →
                  </span>
                </Link>
                <Link
                  href="/officer"
                  className="group flex flex-1 items-center justify-between rounded-xl border border-line bg-surface px-5 py-4 transition-colors hover:border-cobalt"
                >
                  <span>
                    <span className="block text-base font-semibold text-ink">
                      I’m with the traffic police
                    </span>
                    <span className="text-sm text-ink-muted">
                      Hotspots · patrol plan · targets
                    </span>
                  </span>
                  <span className="text-xl text-cobalt transition-transform group-hover:translate-x-0.5">
                    →
                  </span>
                </Link>
              </div>
            </div>

            <div className="reveal" style={{ animationDelay: "0.2s" }}>
              <CityMap />
            </div>
          </div>

          <div className="mx-auto w-full max-w-6xl px-5 pb-10 sm:px-8">
            <ActivityTicker />
          </div>
        </section>

        <LandingStats />
      </main>
      <Footer />
    </>
  );
}
