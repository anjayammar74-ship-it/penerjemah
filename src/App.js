import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import Home from "@/pages/Home";
import Reader from "@/pages/Reader";
import Share from "@/pages/Share";
import Series from "@/pages/Series";
import { OfflineBanner } from "@/components/OfflineBanner";
import { PullToRefresh } from "@/components/PullToRefresh";

function App() {
  return (
    <BrowserRouter>
      <OfflineBanner />
      <PullToRefresh />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/read" element={<Reader />} />
        <Route path="/share" element={<Share />} />
        <Route path="/series" element={<Series />} />
      </Routes>
      <Toaster theme="dark" position="top-center" richColors />
    </BrowserRouter>
  );
}

export default App;
