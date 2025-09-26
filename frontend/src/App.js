import "./App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Terminal from "./components/Terminal";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Terminal />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
