import { useState } from "react";
import axios from "axios";
import "./styles.css"; // Import CSS for styling

export default function App() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const search = async () => {
    if (!query) return;
    setLoading(true);
    try {
      const response = await axios.get(`http://localhost:5000/search?q=${query}`);
      setResults(response.data); // Assuming response is a list of URLs
    } catch (error) {
      console.error("Search failed", error);
      setResults([]);
    }
    setLoading(false);
  };

  return (
    <div className="container">
      {/* Navbar */}
      <nav className="navbar">
        <h1>CS4675 Vector Search: Next.JS Docs</h1>
        <div className="nav-links">
          <a href="https://github.com/cduffy8/cs4675-group-4" target="_blank" rel="noopener noreferrer">
            <img src="/assets/github.png" alt="GitHub" />
          </a>
          <a href="https://nextjs.org/docs" target="_blank" rel="noopener noreferrer">
            <img src="/assets/nextjs.png" alt="Next.JS Docs" />
          </a>
        </div>
      </nav>

      {/* Search Box */}
      <div className="search-container">
        <input
          type="text"
          className="search-input"
          placeholder="Enter search query..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button onClick={search} className="search-button">Search</button>
      </div>

      {/* Results */}
      <div className="results">
        {loading && <p className="loading-text">Searching...</p>}
        {results.map((link, index) => (
          <div key={index} className="result-item">
            <a href={link} target="_blank" rel="noopener noreferrer">
              {link}
            </a>
          </div>
        ))}
      </div>
    </div>
  );
}
