import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import FindParking from "@/components/FindParking";
import ResidentCommunity from "@/components/ResidentCommunity";

export default function ResidentPage() {
  return (
    <>
      <Nav />
      <main>
        <FindParking index="01" />
        <ResidentCommunity index="02" />
      </main>
      <Footer />
    </>
  );
}
