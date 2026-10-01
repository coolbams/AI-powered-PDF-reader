import Header from "./components/Header";
import ThreeBodiedPane from "./components/ThreeBodiedPane";

// This is the top-level app component.
// It is the root of the React frontend and decides which main layout to show.
export default function App() {
  return (
    <div className="h-screen flex flex-col px-8 bg-[#0E0E0E] overflow-hidden">
      {/* Header sits at the top of the page */}
      <Header />

      {/* Main dashboard layout: upload sidebar + PDF viewer + chatbot */}
      <ThreeBodiedPane />
    </div>
  );
}