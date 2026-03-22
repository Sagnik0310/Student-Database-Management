import React from "react";
import "./App.css";
import Navbar from "./components/Navbar";
import Dashboard from "./pages/Dashboard";
import About from "./pages/About";

function App() {

  const path = window.location.pathname;

  let Page;

  if (path === "/about") {
    Page = <About />;
  } else {
    Page = <Dashboard />;
  }

  return (
    <div className="App">
      <Navbar />
      {Page}
    </div>
  );
}

export default App;