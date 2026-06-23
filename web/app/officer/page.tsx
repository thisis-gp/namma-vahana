import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import OfficerConsole from "@/components/officer/OfficerConsole";

export default function OfficerPage() {
  return (
    <>
      <Nav />
      <main>
        <OfficerConsole />
      </main>
      <Footer />
    </>
  );
}
