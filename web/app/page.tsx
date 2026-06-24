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
              "radial-gradient(90% 70% at 92% 8%, rgba(30,69,200,0.14) 0%, rgba(236,239,243,0) 58%), linear-gradient(180deg, #f8fbff 0%, var(--ground) 100%)",
          }}
        >
          <div className="mx-auto grid w-full max-w-[92rem] items-center gap-10 px-5 pb-12 pt-14 sm:px-8 sm:pb-16 sm:pt-20 lg:grid-cols-[0.72fr_1.28fr] xl:gap-14">
            <div className="relative z-10">
              <h1
                className="font-display reveal max-w-2xl text-4xl font-extrabold leading-[0.98] tracking-tight text-ink sm:text-6xl lg:text-[4.4rem]"
                style={{ animationDelay: "0.08s" }}
              >
                Parking intelligence for{" "}
                <span className="text-cobalt">Namma Bengaluru</span>
              </h1>
              <p
                className="reveal mt-5 max-w-xl text-lg leading-relaxed text-ink-muted"
                style={{ animationDelay: "0.16s" }}
              >
                Find safer parking, avoid fines, and help traffic police
                prioritize patrols using real Bengaluru violation intelligence.
              </p>
              <div
                className="reveal mt-5 flex flex-wrap items-center gap-2 font-mono text-[0.68rem] uppercase tracking-wider text-ink-muted"
                style={{ animationDelay: "0.2s" }}
              >
                <span className="rounded-full border border-line bg-white/75 px-3 py-1">
                  {BRAND.tagline}
                </span>
                <span className="rounded-full border border-line bg-white/75 px-3 py-1">
                  2,98,443 violations analyzed
                </span>
              </div>

              {/* Two doors */}
              <div
                className="reveal mt-8 grid gap-3 sm:grid-cols-2"
                style={{ animationDelay: "0.24s" }}
              >
                <Link
                  href="/resident"
                  className="group flex min-h-28 items-center justify-between rounded-xl border border-cobalt/30 bg-white px-5 py-4 shadow-[0_18px_50px_-30px_rgba(30,69,200,0.65)] transition-all hover:-translate-y-0.5 hover:border-cobalt hover:shadow-[0_24px_60px_-32px_rgba(30,69,200,0.75)]"
                >
                  <span className="flex items-center gap-4">
                    <span className="grid h-12 w-12 place-items-center rounded-full bg-cobalt text-lg font-bold text-white">
                      R
                    </span>
                    <span>
                      <span className="block text-base font-semibold text-ink">
                        Resident
                      </span>
                      <span className="text-sm text-ink-muted">
                        Find parking
                      </span>
                    </span>
                  </span>
                  <span className="text-xl text-cobalt transition-transform group-hover:translate-x-0.5">
                    →
                  </span>
                </Link>
                <Link
                  href="/officer"
                  className="group flex min-h-28 items-center justify-between rounded-xl border border-amber/45 bg-white px-5 py-4 shadow-[0_18px_50px_-34px_rgba(244,161,0,0.7)] transition-all hover:-translate-y-0.5 hover:border-amber hover:shadow-[0_24px_60px_-34px_rgba(244,161,0,0.8)]"
                >
                  <span className="flex items-center gap-4">
                    <span className="grid h-12 w-12 place-items-center rounded-full bg-amber text-lg font-bold text-white">
                      P
                    </span>
                    <span>
                      <span className="block text-base font-semibold text-ink">
                        Traffic police
                      </span>
                      <span className="text-sm text-ink-muted">
                        Command map
                      </span>
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
