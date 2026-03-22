import React from "react";

function Navbar() {
  return (
    <nav className="navbar">
      <h2>StudentDB</h2>

      <div>
        <a href="/">Dashboard</a>
        <a href="/about">About</a>
      </div>
    </nav>
  );
}

export default Navbar;